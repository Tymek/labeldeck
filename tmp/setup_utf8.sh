#!/bin/bash
# UTF-8 setup script for Raspberry Pi

echo "Setting up UTF-8 support for Polish characters..."

# 1. Configure locales
echo "1. Configuring locales..."
sudo dpkg-reconfigure locales --frontend=noninteractive || true

# Generate required locales
# sudo locale-gen en_US.UTF-8
# sudo locale-gen pl_PL.UTF-8

# 2. Set system-wide locale
echo "2. Setting system locale..."
sudo update-locale LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8

# 3. Set current session locale
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export PYTHONIOENCODING=utf-8

# 4. Configure console for UTF-8
echo "3. Configuring console..."
sudo dpkg-reconfigure console-setup --frontend=noninteractive || true

# 5. Add to ~/.bashrc for persistence
echo "4. Adding to ~/.bashrc..."
grep -q "export LANG=en_US.UTF-8" ~/.bashrc || echo "export LANG=en_US.UTF-8" >> ~/.bashrc
grep -q "export LC_ALL=en_US.UTF-8" ~/.bashrc || echo "export LC_ALL=en_US.UTF-8" >> ~/.bashrc
grep -q "export PYTHONIOENCODING=utf-8" ~/.bashrc || echo "export PYTHONIOENCODING=utf-8" >> ~/.bashrc

# 6. Install required fonts that support Polish characters
echo "5. Installing fonts with Polish character support..."
sudo apt-get update
sudo apt-get install -y fonts-dejavu-core fonts-liberation ttf-ubuntu-font-family

# 7. Test UTF-8 support
echo "6. Testing UTF-8 support..."
echo "Polish characters test: ąćęłńóśźż ĄĆĘŁŃÓŚŹŻ"

python3 -c "
import sys
import locale

print('Python UTF-8 test:')
print('Default encoding:', sys.getdefaultencoding())
print('Stdin encoding:', sys.stdin.encoding)
print('Stdout encoding:', sys.stdout.encoding)
print('File system encoding:', sys.getfilesystemencoding())

try:
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    print('Locale set to en_US.UTF-8 successfully')
except:
    print('Warning: Could not set locale to en_US.UTF-8')

test_chars = 'ąćęłńóśźż'
print(f'Polish chars: {test_chars}')
print('Character codes:', [ord(c) for c in test_chars])
"

echo ""
echo "UTF-8 setup complete!"
echo "Please restart your terminal or run: source ~/.bashrc"
echo ""
echo "To test, try typing Polish characters in the label printer:"
echo "  ą ć ę ł ń ó ś ź ż"
