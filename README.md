
## BOM (in PLN)

- Raspberry Pi Zero W - 100zł
- Dymo 450 - 250zł
- Display - 40zł
- Cables - 50zł
- Pi USB Hub (B) - 30zł
- Case (55015FX) - 130zł
---
Total: ~600zł

Build for Raspberry Pi
-----------------------

### Cross-compile

#### Check Pi Architecture
```bash
# On your Pi, check which architecture to build for:
uname -m
# armv6l, armv7l → use linux/arm/v7
# aarch64 → use linux/arm64
```

#### Build – **For Raspberry Pi Zero (32-bit ARM):**
```bash
docker buildx build \
  --platform linux/arm/v7 \
  --tag registry.scrlk.pl/labeldeck:latest \
  --push .

# Deploy and Run on Pi
docker pull registry.scrlk.pl/labeldeck:latest
docker run -d --name labeldeck -v $(pwd)/app:/app registry.scrlk.pl/labeldeck:latest
# TODO: pull repository
```

### Alternative: **Save/load image file (no registry needed):**
```bash
docker buildx build --platform linux/arm64 -t labeldeck:latest --output type=docker,dest=labeldeck-pi.tar .

scp labeldeck-pi.tar pi@raspberrypi.local:~/

docker load < labeldeck-pi.tar
docker run -d --name labeldeck -v $(pwd)/app:/app labeldeck:latest
```
