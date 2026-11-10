#!/usr/bin/env bash
# Gera o executável para Linux em dist/SomDeMala-linux.tar.gz
# Uso: bash build_linux.sh
set -euo pipefail
cd "$(dirname "$0")"
APP=SomDeMala

echo ">> Preparando ambiente de build"
python3 -m venv .venv-build
PY=.venv-build/bin/python
$PY -m pip install -q -U pip
$PY -m pip install -q -U yt-dlp PySide6 pyinstaller

if [ ! -f ffmpeg-bin/ffmpeg ] || [ ! -f ffmpeg-bin/ffprobe ]; then
  echo ">> Baixando FFmpeg estático (não depende de nada no sistema)"
  # ffprobe: o yt-dlp usa para inspecionar os arquivos ao converter e juntar vídeo + áudio
  mkdir -p ffmpeg-bin
  curl -L --fail -o ffmpeg.tar.xz \
    https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz
  tar -xf ffmpeg.tar.xz -C ffmpeg-bin --strip-components=2 --wildcards '*/bin/ffmpeg' '*/bin/ffprobe'
  rm ffmpeg.tar.xz
fi

echo ">> Empacotando"
$PY -m PyInstaller --noconfirm --clean --windowed --name "$APP" \
  --add-binary "ffmpeg-bin/ffmpeg:." \
  --add-binary "ffmpeg-bin/ffprobe:." \
  SomDeMala.py

cd dist
tar -czf "$APP-linux.tar.gz" "$APP"
echo ">> Pronto: dist/$APP-linux.tar.gz"
echo "   Para abrir: extraia e rode ./$APP/$APP"
