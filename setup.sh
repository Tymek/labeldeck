#!/usr/bin/env bash
set -euo pipefail

# Pi Zero W setup script for LabelDeck

echo "[1/2] Installing system packages (requires sudo)…"
sudo apt-get update
sudo apt-get install -y \
  python3 python3-venv python3-pip \
  cups cups-client cups-bsd \
  ghostscript \
  fonts-dejavu-core \
  libjpeg-dev zlib1g-dev \
  imagemagick \
  wget screenfetch htop

echo "[2/2] Enabling CUPS and user permissions…"
sudo usermod -a -G lpadmin "$USER" || true
sudo systemctl enable cups --now

echo "[2/5] Creating Python venv and installing deps…"
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt

echo "Done."
