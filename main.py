from flask import Flask, render_template, request, Response
import subprocess
import shlex
import threading
import queue
import os
import re

app = Flask(__name__)

# File d'attente pour la sortie de yt-dlp
output_queue = queue.Queue()

def run_yt_dlp(url):
    """Exécute run_yt_dlp.sh et capture la sortie, titre et progression."""
    # Récupérer le titre de la vidéo
    try:
        title_cmd = f"yt-dlp --get-title {shlex.quote(url)}"
        title = subprocess.check_output(shlex.split(title_cmd), text=True, encoding='utf-8', errors='replace').strip()
        output_queue.put(f"title: {title}")
    except subprocess.CalledProcessError:
        output_queue.put("title: Erreur lors de la récupération du titre")
    except Exception as e:
        output_queue.put(f"title: Erreur : {str(e)}")

    # Exécuter le script de téléchargement
    script_path = os.path.join("scripts", "run_yt_dlp.sh")
    if not os.path.isfile(script_path):
        output_queue.put(f"❌ Erreur : Script {script_path} introuvable")
        return
    command = f"bash {script_path} {shlex.quote(url)}"
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
        progress_re = re.compile(r'\[download\]\s+(\d+\.\d)%')
        for line in iter(process.stdout.readline, ''):
            line = line.strip()
            # Chercher le pourcentage dans les lignes [download]
            match = progress_re.search(line)
            if match:
                percentage = match.group(1)
                output_queue.put(f"progress: {percentage}")
            output_queue.put(line)
        process.wait()
        if process.returncode == 0:
            output_queue.put("✅ Téléchargement terminé !")
        else:
            output_queue.put(f"❌ Erreur : code {process.returncode}")
    except FileNotFoundError as e:
        output_queue.put(f"❌ Erreur : Commande bash ou script introuvable : {str(e)}")
    except Exception as e:
        output_queue.put(f"❌ Erreur exécution : {str(e)}")

@app.route('/')
def index():
    """Affiche la page principale avec le formulaire."""
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    """Lance le téléchargement via run_yt_dlp.sh."""
    url = request.form.get('url')
    if not url:
        return "❌ URL manquante !", 400
    # Vide la queue pour un nouveau téléchargement
    while not output_queue.empty():
        output_queue.get()
    # Lance en thread
    threading.Thread(target=run_yt_dlp, args=(url,), daemon=True).start()
    return "🚀 Téléchargement démarré...", 200

@app.route('/stream')
def stream():
    """Stream la sortie en SSE."""
    def generate():
        while True:
            try:
                line = output_queue.get_nowait()
                if line:
                    yield f"data: {line}\n\n"
            except queue.Empty:
                yield ": keepalive\n\n"
    return Response(generate(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache'})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5011, debug=True)