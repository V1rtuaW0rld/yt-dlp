#!/bin/bash

# Horodatage
timestamp=$(date +"%Y-%m-%d_%H-%M-%S")

# Dossier de sortie sur NAS
output_dir="/mnt/nas/video/yt-dlp"
mkdir -p "$output_dir"

# Log
log_file="./logs/download_$timestamp.log"
touch "$log_file"

# URL à télécharger
URL="$1"

if [[ -z "$URL" ]]; then
  echo "Erreur : aucun lien fourni. Usage : ./run_yt_dlp.sh <URL>" | tee -a "$log_file"
  exit 1
fi

# Commande yt-dlp sérieuse
yt_dlp_bin="$(which yt-dlp)"

"$yt_dlp_bin" \
  --progress \
  --socket-timeout 60 \
  --retries 20 \
  --fragment-retries 10 \
  --concurrent-fragments 4 \
  -f "bv*+ba/bestvideo+bestaudio/best" \
  -o "$output_dir/%(title)s.%(ext)s" \
  "$URL" 2>&1 | tee -a "$log_file"
