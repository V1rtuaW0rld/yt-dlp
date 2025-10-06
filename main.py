from flask import Flask, render_template, request, Response
import subprocess
import shlex
import threading
import queue
import os
import re
import uuid
import json
from bdd import db
import time
import sqlite3

app = Flask(__name__)

output_queue = queue.Queue()

def run_yt_dlp(url, task_id):
    print(f"Démarrage de la tâche {task_id} pour {url} (vidéo)")
    try:
        json_cmd = f"yt-dlp --restrict-filenames --dump-json {shlex.quote(url)}"
        print(f"Exécution de la commande JSON : {json_cmd}")
        result = subprocess.run(shlex.split(json_cmd), capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
        if result.returncode == 0 and result.stdout.strip():
            try:
                video_info = json.loads(result.stdout.strip())
                title = video_info.get('title', 'Titre inconnu')
                thumbnail = video_info.get('thumbnail', '')
                duration_string = video_info.get('duration_string', 'N/A')
                filesize_approx = video_info.get('filesize_approx', None)
                resolution = video_info.get('resolution', 'N/A')
                filename = f"{title}.{video_info.get('ext', 'mp4')}"

                if filesize_approx:
                    if filesize_approx >= 1_000_000_000:
                        filesize_approx = f"{filesize_approx / 1_000_000_000:.2f} Go"
                    elif filesize_approx >= 1_000_000:
                        filesize_approx = f"{filesize_approx / 1_000_000:.2f} Mo"
                    else:
                        filesize_approx = f"{filesize_approx / 1_000:.2f} Ko"
                else:
                    filesize_approx = 'N/A'

                db.add_task(task_id, title, thumbnail, duration_string, filesize_approx, resolution, filename, url, 'video')
                task = db.get_task_by_id(task_id)
                output_queue.put(f"[{task_id}] VideoInfo: {json.dumps({'task_id': task_id, 'date': task[0], 'title': title, 'thumbnail': thumbnail, 'duration_string': duration_string, 'filesize_approx': filesize_approx, 'resolution': resolution, 'filename': filename, 'progress': 0, 'status': task[10], 'type': 'video'})}")
            except json.JSONDecodeError as e:
                output_queue.put(f"[{task_id}] ❌ Erreur lors du parsing JSON : {str(e)}")
                return
        else:
            output_queue.put(f"[{task_id}] ❌ Erreur ou JSON vide : {result.stderr}")
            return
    except subprocess.TimeoutExpired as e:
        output_queue.put(f"[{task_id}] ❌ Timeout lors de la récupération des informations")
        return
    except Exception as e:
        output_queue.put(f"[{task_id}] ❌ Erreur inattendue : {str(e)}")
        return

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
        progress_re = re.compile(r'\[download\]\s+(\d+\.\d+)%')
        for line in iter(process.stdout.readline, ''):
            line = line.strip()
            if line:
                match = progress_re.search(line)
                if match:
                    percentage = float(match.group(1))
                    db.update_progress(task_id, percentage)
                    output_queue.put(f"[{task_id}] Progress: {percentage}")
                output_queue.put(f"[{task_id}] {line}")
        process.wait()
        if process.returncode == 0:
            db.update_progress(task_id, 100)
            output_queue.put(f"[{task_id}] ✅ Téléchargement terminé !")
            task = db.get_task_by_id(task_id)
            output_queue.put(f"[{task_id}] VideoInfo: {json.dumps({'task_id': task_id, 'status': task[10], 'type': task[11]})}")
        else:
            output_queue.put(f"[{task_id}] ❌ Erreur : code {process.returncode}")
    except FileNotFoundError as e:
        output_queue.put(f"[{task_id}] ❌ Erreur : Commande bash ou script introuvable : {str(e)}")
    except Exception as e:
        output_queue.put(f"[{task_id}] ❌ Erreur exécution : {str(e)}")

def run_yt_dlp_audio(url, task_id):
    print(f"Démarrage de la tâche {task_id} pour {url} (audio)")
    # Récupération des métadatas en premier
    try:
        json_cmd = f"yt-dlp --restrict-filenames --dump-json {shlex.quote(url)}"
        print(f"Exécution de la commande JSON : {json_cmd}")
        result = subprocess.run(shlex.split(json_cmd), capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
        if result.returncode == 0 and result.stdout.strip():
            try:
                video_info = json.loads(result.stdout.strip())
                title = video_info.get('title', 'Titre inconnu')
                thumbnail = video_info.get('thumbnail', '')  # Récupérer la miniature
                duration_string = video_info.get('duration_string', 'N/A')
                filesize_approx = video_info.get('filesize_approx', None)
                resolution = 'N/A'  # Pas de résolution pour audio
                filename = f"{title}.mp3"

                if filesize_approx:
                    if filesize_approx >= 1_000_000_000:
                        filesize_approx = f"{filesize_approx / 1_000_000_000:.2f} Go"
                    elif filesize_approx >= 1_000_000:
                        filesize_approx = f"{filesize_approx / 1_000_000:.2f} Mo"
                    else:
                        filesize_approx = f"{filesize_approx / 1_000:.2f} Ko"
                else:
                    filesize_approx = 'N/A'

                # Stocker les métadatas dans la BDD, même sans téléchargement
                db.add_task(task_id, title, thumbnail, duration_string, filesize_approx, resolution, filename, url, 'audio')
                task = db.get_task_by_id(task_id)
                output_queue.put(f"[{task_id}] VideoInfo: {json.dumps({'task_id': task_id, 'date': task[0], 'title': title, 'thumbnail': thumbnail, 'duration_string': duration_string, 'filesize_approx': filesize_approx, 'resolution': resolution, 'filename': filename, 'progress': 0, 'status': task[10], 'type': 'audio'})}")
            except json.JSONDecodeError as e:
                output_queue.put(f"[{task_id}] ❌ Erreur lors du parsing JSON : {str(e)}")
                return
        else:
            output_queue.put(f"[{task_id}] ❌ Erreur ou JSON vide : {result.stderr}")
            return
    except subprocess.TimeoutExpired as e:
        output_queue.put(f"[{task_id}] ❌ Timeout lors de la récupération des informations")
        return
    except Exception as e:
        output_queue.put(f"[{task_id}] ❌ Erreur inattendue : {str(e)}")
        return

    # Lancement du téléchargement
    script_path = os.path.join("scripts", "run_yt_dlp_audio.sh")
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
        progress_re = re.compile(r'\[download\]\s+(\d+\.\d+)%')
        for line in iter(process.stdout.readline, ''):
            line = line.strip()
            if line:
                match = progress_re.search(line)
                if match:
                    percentage = float(match.group(1))
                    db.update_progress(task_id, percentage)
                    output_queue.put(f"[{task_id}] Progress: {percentage}")
                output_queue.put(f"[{task_id}] {line}")
        process.wait()
        if process.returncode == 0:
            db.update_progress(task_id, 100)
            output_queue.put(f"[{task_id}] ✅ Téléchargement terminé !")
            task = db.get_task_by_id(task_id)
            output_queue.put(f"[{task_id}] VideoInfo: {json.dumps({'task_id': task_id, 'status': task[10], 'type': task[11]})}")
        else:
            output_queue.put(f"[{task_id}] ❌ Erreur : code {process.returncode} - {line}")
    except FileNotFoundError as e:
        output_queue.put(f"[{task_id}] ❌ Erreur : Commande bash ou script introuvable : {str(e)}")
    except Exception as e:
        output_queue.put(f"[{task_id}] ❌ Erreur exécution : {str(e)}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    url = request.form.get('url')
    if not url:
        return "❌ URL manquante !", 400
    urls = [u.strip() for u in url.split(',') if u.strip()]
    for url in urls:
        task_id = str(uuid.uuid4())
        threading.Thread(target=run_yt_dlp, args=(url, task_id), daemon=True).start()
        print(f"Tâche {task_id} lancée pour {url} (vidéo)")
    return "🚀 Téléchargement(s) vidéo démarré(s)...", 200

@app.route('/download-audio', methods=['POST'])
def download_audio():
    url = request.form.get('url')
    if not url:
        return "❌ URL manquante !", 400
    # Vérification basique de l'URL
    if not url.startswith(('http://', 'https://')):
        return "❌ URL invalide !", 400
    urls = [u.strip() for u in url.split(',') if u.strip()]
    for url in urls:
        task_id = str(uuid.uuid4())
        threading.Thread(target=run_yt_dlp_audio, args=(url, task_id), daemon=True).start()
        print(f"Tâche {task_id} lancée pour {url} (audio)")
    return "🚀 Téléchargement(s) audio démarré(s)...", 200

@app.route('/resume', methods=['POST'])
def resume():
    task_id = request.form.get('task_id')
    if not task_id:
        return "❌ task_id manquant !", 400
    task = db.get_task_by_id(task_id)
    if not task or not task[9]:  # task[9] est original_url
        return f"❌ Tâche {task_id} non trouvée ou URL absente", 404
    original_url = task[9]
    task_type = task[11]  # task[11] est type (video ou audio)
    
    # Mettre à jour status avec un nouveau timestamp
    import time
    new_timestamp = str(int(time.time()))  # Convertir en string pour TEXT
    db.update_status(task_id, new_timestamp)
    
    # Lancer la reprise selon le type
    if task_type == 'video':
        threading.Thread(target=run_yt_dlp, args=(original_url, task_id), daemon=True).start()
        return f"🚀 Reprise de la tâche {task_id} (vidéo) avec {original_url}", 200
    elif task_type == 'audio':
        threading.Thread(target=run_yt_dlp_audio, args=(original_url, task_id), daemon=True).start()
        return f"🚀 Reprise de la tâche {task_id} (audio) avec {original_url}", 200
    else:
        return f"❌ Type de tâche {task_type} inconnu pour {task_id}", 400

@app.route('/stream')
def stream():
    page = int(request.args.get('page', 1))
    per_page = 5
    def generate():
        tasks, total_pages, total = db.get_all_tasks_paginated(page, per_page)
        if not tasks:
            print("Aucune tâche trouvée pour la page", page)
        print(f"Page {page} - Tâches chargées: {len(tasks)}, Total pages: {total_pages}, Total items: {total}")
        print(f"Ordre des tâches initiales: {[task[0] for task in tasks]}")
        initial_data = {
            "type": "InitialData",
            "tasks": [{"date": task[0], "task_id": task[1], "title": task[2], "thumbnail": task[3], "duration_string": task[4], "filesize_approx": task[5], "resolution": task[6], "filename": task[7], "progress": task[8], "status": task[10], "type": task[11]} for task in tasks],
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_items": total,
                "per_page": per_page
            }
        }
        yield f"data: {json.dumps(initial_data)}\n\n"
        while True:
            try:
                line = output_queue.get(timeout=1.0)
                if line:
                    print(f"Mise à jour envoyée: {line}")
                    yield f"data: {line}\n\n"
            except queue.Empty:
                yield ": keepalive\n\n"
    return Response(generate(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache', 'Connection': 'keep-alive'})

if __name__ == '__main__':
    print("Démarrage du serveur Flask...")
    sentinelle_path = os.path.join("scripts", "sentinelle.sh")
    if os.path.isfile(sentinelle_path):
        print(f"Lancement de {sentinelle_path} en arrière-plan...")
        threading.Thread(
            target=lambda: subprocess.call(["bash", sentinelle_path]),
            daemon=True
        ).start()
    else:
        print(f"⚠️ Script {sentinelle_path} introuvable. sentinelle.sh ne sera pas lancé.")
    app.run(host="0.0.0.0", port=5011, debug=True)