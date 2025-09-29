from flask import Flask, request, render_template
import subprocess

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/download", methods=["POST"])
def download():
    url = request.form.get("url")
    if not url:
        return "Erreur : aucune URL fournie", 400

    try:
        subprocess.run(["./scripts/run_yt_dlp.sh", url], check=True)
        return f"Téléchargement lancé pour : {url}"
    except subprocess.CalledProcessError as e:
        return f"Échec du téléchargement : {e}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5011, debug=True)
