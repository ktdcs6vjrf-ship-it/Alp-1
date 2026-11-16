#!/bin/bash
# voir-video.sh URL [DOSSIER] — télécharge une vidéo (TikTok, Instagram, YouTube…) et en fait une planche d'images.
set -euo pipefail
URL="$1"; OUT="${2:-$PWD/video-$(date +%s)}"; ENV="${VIDEO_ENV:-${TMPDIR:-/tmp}/voir-video-env}"
[ -x "$ENV/bin/yt-dlp" ] || { python3 -m venv "$ENV" && "$ENV/bin/pip" install -q yt-dlp imageio-ffmpeg; }
FFMPEG=$("$ENV/bin/python" -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())")
mkdir -p "$OUT"; cd "$OUT"
"$ENV/bin/yt-dlp" --no-progress --restrict-filenames --ffmpeg-location "$FFMPEG" -f "b[height<=720]/b" \
  --write-info-json --write-subs --write-auto-subs --sub-langs "fr.*,en.*" -o "video.%(ext)s" "$URL"
VID=$(ls video.* | grep -vE '\.(json|vtt|srt)$' | head -1)
DUR=$("$ENV/bin/python" -c "import json; print(json.load(open('video.info.json')).get('duration') or 30)")
STEP=$("$ENV/bin/python" -c "print(max(1.0, float($DUR)/12))")
"$FFMPEG" -loglevel error -y -i "$VID" -vf "fps=1/$STEP,scale=360:-1" -frames:v 12 image-%02d.jpg
"$FFMPEG" -loglevel error -y -i "$VID" -vf "fps=1/$STEP,scale=360:-1,tile=4x3:padding=6:color=black" -frames:v 1 planche.jpg
"$ENV/bin/python" - <<'PY'
import json, glob
d = json.load(open("video.info.json"))
print("Titre       :", d.get("title"))
print("Auteur      :", d.get("uploader") or d.get("channel"))
print("Durée       :", d.get("duration"), "s")
print("Description :", (d.get("description") or "")[:500])
subs = glob.glob("*.vtt") + glob.glob("*.srt")
print("Sous-titres :", ", ".join(subs) or "aucun")
PY
echo "Planche     : $OUT/planche.jpg"
