from flask import Flask, render_template, request, Response
import subprocess
import shlex
import threading
import queue
import os
import re
import uuid

app = Flask(__name__)

# File unique pour la sortie
output_queue = queue.Queue()

def run_yt_dlp(url, task_id):
    """Exécute run_yt_dlp.sh et capture la sortie, titre et progression pour une tâche."""
    print(f"Démarrage de la tâche {task_id} pour {url}")  # Débogage
    # Récupérer le titre de la vidéo avec une commande shell
    title = None
    try:
        title_cmd = f"yt-dlp --get-title {shlex.quote(url)}"
        print(f"Exécution de la commande titre : {title_cmd}")  # Débogage
        result = subprocess.run(shlex.split(title_cmd), capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
        if result.returncode == 0 and result.stdout.strip():
            title = result.stdout.strip()
            output_queue.put(f"[{task_id}] Titre récupéré : {title}")  # Injecter dans stdout
            print(f"Titre récupéré pour {task_id}: {title}")  # Débogage
        else:
            output_queue.put(f"[{task_id}] ❌ Erreur ou titre vide : {result.stderr}")
            print(f"Erreur stdout/stderr pour {task_id}: {result.stderr}")
            return  # Arrête si pas de titre
    except subprocess.TimeoutExpired as e:
        output_queue.put(f"[{task_id}] ❌ Timeout lors de la récupération du titre")
        print(f"Timeout pour {task_id}: {str(e)}")
        return
    except Exception as e:
        output_queue.put(f"[{task_id}] ❌ Erreur inattendue : {str(e)}")
        print(f"Exception pour {task_id}: {str(e)}")
        return

    # Exécuter le script de téléchargement
    script_path = os.path.join("scripts", "run_yt_dlp.sh")
    if not os.path.isfile(script_path):
        output_queue.put(f"[{task_id}] ❌ Erreur : Script {script_path} introuvable")
        return
    command = f"bash {script_path} {shlex.quote(url)} {shlex.quote(task_id)}"
    try:
        process = subprocess.Popen(
            shlex.split(command),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        # Regex pour extraire le pourcentage
        progress_re = re.compile(r'\[download\]\s+(\d+\.\d+)%')
        for line in iter(process.stdout.readline, ''):
            line = line.strip()
            if line:  # Ignorer les lignes vides
                match = progress_re.search(line)
                if match:
                    percentage = match.group(1)
                    output_queue.put(f"[{task_id}] Progress: {percentage}")  # Injecter progression
                    print(f"Progression pour {task_id}: {percentage}%")  # Débogage
                output_queue.put(f"[{task_id}] {line}")
        process.wait()
        if process.returncode == 0:
            output_queue.put(f"[{task_id}] ✅ Téléchargement terminé !")
        else:
            output_queue.put(f"[{task_id}] ❌ Erreur : code {process.returncode}")
    except FileNotFoundError as e:
        output_queue.put(f"[{task_id}] ❌ Erreur : Commande bash ou script introuvable : {str(e)}")
    except Exception as e:
        output_queue.put(f"[{task_id}] ❌ Erreur exécution : {str(e)}")

@app.route('/')
def index():
    """Affiche la page principale avec le formulaire."""
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    """Lance un ou plusieurs téléchargements via run_yt_dlp.sh."""
    url = request.form.get('url')
    if not url:
        return "❌ URL manquante !", 400
    # Séparer les URLs par virgule (simplifié sans multitâche pour l'instant)
    urls = [u.strip() for u in url.split(',') if u.strip()]
    for url in urls:
        task_id = str(uuid.uuid4())  # ID unique
        threading.Thread(target=run_yt_dlp, args=(url, task_id), daemon=True).start()
        print(f"Tâche {task_id} lancée pour {url}")  # Débogage
    return "🚀 Téléchargement(s) démarré(s)...", 200

@app.route('/stream')
def stream():
    """Stream la sortie en SSE avec l'ID de la tâche."""
    def generate():
        while True:
            try:
                line = output_queue.get_nowait()
                if line:
                    print(f"Envoi SSE : {line}")  # Débogage
                    yield f"data: {line}\n\n"
            except queue.Empty:
                pass
            yield ": keepalive\n\n"
    return Response(generate(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache'})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5011, debug=True)