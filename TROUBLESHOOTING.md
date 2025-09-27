# Troubleshooting Guide

## Common Issues and Solutions

### 1. OLED Display Not Working

**Error**: `OLED display not available: No module named 'oled_display'`
- **Solution**: Make sure `oled_display.py` is in the same directory as `main.py`
- **Check**: Run `ls -la oled_display.py` to verify the file exists

**Error**: `Failed to initialize OLED: [various I2C errors]`
- **Solution**: Check I2C connection and address
- **Check**: Run `i2cdetect -y 1` to see if your display is detected (usually at 0x3c or 0x3d)
- **Fix wiring**: 
  - VCC → 3.3V (Pin 1 or 17)
  - GND → Ground (Pin 6, 9, 14, 20, 25, 30, 34, or 39)
  - SDA → GPIO 2 (Pin 3)
  - SCL → GPIO 3 (Pin 5)

### 2. Printer Issues

**Error**: `lp: Error - The printer or class does not exist.`
- **Solution**: Configure your printer in CUPS
- **Steps**:
  1. Open CUPS web interface: http://localhost:631
  2. Go to "Administration" → "Add Printer"
  3. Select your DYMO printer
  4. Set name to match your config (default: "dymo450")

**Error**: `convert-im6.q16: attempt to perform an operation not allowed by the security policy 'PDF'`
- **Solution**: Fix ImageMagick security policy
- **Command**: 
  ```bash
  sudo sed -i 's/policy domain="coder" rights="none" pattern="PDF"/policy domain="coder" rights="read|write" pattern="PDF"/' /etc/ImageMagick-6/policy.xml
  ```

### 3. Environment Configuration

Set these environment variables for your specific setup:

```bash
# Printer name (check with: lpstat -p)
export PRINTER="your_printer_name"

# Label size (default is for 36x89mm DYMO labels)
export PILABEL_MEDIA="w102h252"

# OLED I2C address (if different from default 0x3c)
export OLED_I2C_ADDRESS="0x3d"
```

### 4. Testing Commands

```bash
# Check I2C devices
i2cdetect -y 1

# Check available printers
lpstat -p

# Check printer queues
lpstat -t

# Test OLED display
python3 -c "from oled_display import OLEDDisplay; d=OLEDDisplay(); d.test_display()"

# Test label printing (after fixing ImageMagick policy)
echo "Test" | python3 main.py
```

### 5. Dependencies

Make sure all required packages are installed:
```bash
# System packages
sudo apt install i2c-tools libi2c-dev printer-driver-dymo imagemagick

# Python packages
pip install luma.oled RPi.GPIO pillow flask
```

### 6. Permissions

Add your user to required groups:
```bash
sudo usermod -a -G i2c,lp,lpadmin $USER
# Logout and login again for changes to take effect
```
