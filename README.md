
## BOM (in PLN)

- Raspberry Pi Zero W - 100zł
- Dymo 450 - 250zł
- Display - 40zł
- Cables - 50zł
- Pi USB Hub (B) - 30zł
- Case (55015FX) - 130zł
---
Total: ~600zł

Setup for Raspberry Pi Zero
-----------------------

1. Install base image on SD card. "PI Imager" app is the recommended way. Pick Raspberry Pi OS **Lite** (32-bit) as the base image. Better customize config now, but you can do it later with `sudo raspi-config`.

2. Add empty 'ssh' file to the boot directory (optional).

3. Clone this repository 

```bash
sudo apt-get install -y git
git clone https://github.com/Tymek/labeldeck.git /tmp/app
sudo mkdir /app && sudo chown -R "$USER:$USER" /app && sudo mv /tmp/app/* /app/ && cd /app
```

4. Install dependencies

```bash
./setup.sh
```
