from flask import Flask, render_template, request, Response
import subprocess
import shlex
import threading
import queue
import os
import re
import uuid
import json  # Ajouté pour parser le JSON

app = Flask(__name__)

# File unique pour la sortie
output_queue = queue.Queue()

def run_yt_dlp(url, task_id):
    """Exécute run_yt_dlp.sh et capture la sortie, informations vidéo et progression pour une tâche."""
    print(f"Démarrage de la tâche {task_id} pour {url}")  # Débogage
    # Récupérer les informations de la vidéo avec yt-dlp --dump-json
    try:
        json_cmd = f"yt-dlp --dump-json {shlex.quote(url)}"
        print(f"Exécution de la commande JSON : {json_cmd}")  # Débogage
        result = subprocess.run(shlex.split(json_cmd), capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
        if result.returncode == 0 and result.stdout.strip():
            try:
                video_info = json.loads(result.stdout.strip())
                # Extraire les champs demandés
                title = video_info.get('title', 'Titre inconnu')
                thumbnail = video_info.get('thumbnail', '')  # URL de la miniature
                duration_string = video_info.get('duration_string', 'N/A')  # Format hh:mm:ss
                filesize_approx = video_info.get('filesize_approx', None)  # En octets, à formater
                resolution = video_info.get('resolution', 'N/A')  # Résolution (ex. 1920x1080)
                filename = video_info.get('filename', 'N/A')  # Nom du fichier prévu

                # Formater filesize_approx en Mo ou Go
                if filesize_approx:
                    if filesize_approx >= 1_000_000_000:  # Go
                        filesize_approx = f"{filesize_approx / 1_000_000_000:.2f} Go"
                    elif filesize_approx >= 1_000_000:  # Mo
                        filesize_approx = f"{filesize_approx / 1_000_000:.2f} Mo"
                    else:  # Ko
                        filesize_approx = f"{filesize_approx / 1_000:.2f} Ko"
                else:
                    filesize_approx = 'N/A'

                # Envoyer les informations dans la file avec un format clair
                info_dict = {
                    'title': title,
                    'thumbnail': thumbnail,
                    'duration_string': duration_string,
                    'filesize_approx': filesize_approx,
                    'resolution': resolution,
                    'filename': filename
                }
                output_queue.put(f"[{task_id}] VideoInfo: {json.dumps(info_dict)}")
                print(f"Informations récupérées pour {task_id}: {info_dict}")  # Débogage
            except json.JSONDecodeError as e:
                output_queue.put(f"[{task_id}] ❌ Erreur lors du parsing JSON : {str(e)}")
                print(f"Erreur JSON pour {task_id}: {str(e)}")
                return
        else:
            output_queue.put(f"[{task_id}] ❌ Erreur ou JSON vide : {result.stderr}")
            print(f"Erreur stdout/stderr pour {task_id}: {result.stderr}")
            return
    except subprocess.TimeoutExpired as e:
        output_queue.put(f"[{task_id}] ❌ Timeout lors de la récupération des informations")
        print(f"Timeout pour {task_id}: {str(e)}")
        return
    except Exception as e:
        output_queue.put(f"[{task_id}] ❌ Erreur inattendue : {str(e)}")
        print(f"Exception pour {task_id}: {str(e)}")
        return

    # Exécuter le script de téléchargement (inchangé)
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
                    output_queue.put(f"[{task_id}] Progress: {percentage}")
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