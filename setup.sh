#!/usr/bin/env bash
set -euo pipefail

# Pi Zero W setup script for LabelDeck

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$APP_DIR/.venv"

echo "[1/4] Installing system packages (requires sudo)…"
sudo apt-get update
sudo apt-get install -y \
  python3 python3-venv python3-pip \
  cups cups-client cups-bsd \
  ghostscript \
  fonts-dejavu-core fonts-ubuntu \
  libjpeg-dev zlib1g-dev \
  imagemagick \
  wget lsb-release curl screenfetch htop \
  i2c-tools libi2c-dev \
  printer-driver-dymo

echo "[2/4] Enabling I2C interface…"
if command -v raspi-config >/dev/null 2>&1; then
  echo "Enabling I2C via raspi-config..."
  sudo raspi-config nonint do_i2c 0
else
  echo "Adding I2C to /boot/config.txt..."
  if ! grep -q "dtparam=i2c_arm=on" /boot/config.txt; then
    echo "dtparam=i2c_arm=on" | sudo tee -a /boot/config.txt
  fi
  if ! grep -q "i2c-dev" /etc/modules; then
    echo "i2c-dev" | sudo tee -a /etc/modules
  fi
fi

echo "[3/4] Enabling CUPS and user permissions…"
sudo usermod -a -G lpadmin,i2c,lp "$USER" || true
sudo systemctl enable cups --now

echo "[4/4] Creating Python venv and installing deps…"
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt

echo "Done."
