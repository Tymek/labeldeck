"""
OLED Display Controller for Adafruit 128x32 SSD1306 OLED
Provides functions to display text, images, and status information on the OLED screen.
"""

from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
from PIL import Image, ImageDraw, ImageFont
import os
import time
from datetime import datetime
from typing import Optional, List


class OLEDDisplay:
    def __init__(self, i2c_port: int = 1, i2c_address: int = 0x3c):
        """
        Initialize the OLED display.
        
        Args:
            i2c_port: I2C port number (typically 1 for Raspberry Pi)
            i2c_address: I2C address of the display (0x3c is common for SSD1306)
        """
        try:
            # Create I2C interface
            serial = i2c(port=i2c_port, address=i2c_address)
            
            # Create device (128x32 OLED)
            self.device = ssd1306(serial, width=128, height=32)
            
            # Load fonts
            self.font_small = self._load_font(size=8)
            self.font_medium = self._load_font(size=10)
            self.font_large = self._load_font(size=12)
            self.font_xlarge = self._load_font(size=16)  # Extra large for preview
            
            self.width = 128
            self.height = 32
            
            print(f"OLED Display initialized successfully at I2C address {hex(i2c_address)}")
            
        except Exception as e:
            print(f"Failed to initialize OLED display: {e}")
            self.device = None
    
    def _load_font(self, size: int = 10) -> ImageFont.FreeTypeFont:
        """Load a font for the display with Polish character support."""
        try:
            # Priority order: Ubuntu fonts first since they worked via SSH
            font_paths = [
                # Project bundled fonts (check these first)
                "static/fonts/Ubuntu-MediumItalic.ttf",
                "static/fonts/B612Mono-Regular.ttf",
                # Ubuntu system fonts (prioritized since they worked)
                "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
                "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
                "/usr/share/fonts/truetype/ubuntu/Ubuntu-M.ttf",
                # DejaVu fonts (good Unicode support as backup)
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                # Liberation fonts (good fallback)
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
                # More fallbacks
                "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
                "/System/Library/Fonts/Arial.ttf",  # macOS
                "/Windows/Fonts/arial.ttf",  # Windows
            ]
            
            for path in font_paths:
                try:
                    if os.path.exists(path):
                        font = ImageFont.truetype(path, size)
                        # Test if font supports Polish characters
                        test_chars = "ąćęłńóśźż"
                        try:
                            # Try to render Polish characters to verify support
                            from PIL import Image, ImageDraw
                            test_img = Image.new("RGB", (10, 10), "white")
                            test_draw = ImageDraw.Draw(test_img)
                            test_draw.text((0, 0), test_chars, font=font, fill="black")
                            print(f"Using font: {os.path.basename(path)} (supports Polish)")
                            return font
                        except Exception:
                            # Font doesn't support these characters, try next
                            continue
                except (OSError, IOError):
                    continue
            
            # If no font with Polish support found, try any available font
            print("Warning: No font with Polish character support found, using fallback")
            for path in font_paths:
                try:
                    if os.path.exists(path):
                        print(f"Using fallback font: {os.path.basename(path)}")
                        return ImageFont.truetype(path, size)
                except (OSError, IOError):
                    continue
            
            # Fallback to default font
            print("Using PIL default font (limited character support)")
            return ImageFont.load_default()
            
        except Exception:
            return ImageFont.load_default()
    
    def is_available(self) -> bool:
        """Check if the display is available."""
        return self.device is not None
    
    def clear(self):
        """Clear the display."""
        if not self.is_available():
            return
        
        with canvas(self.device) as draw:
            draw.rectangle(self.device.bounding_box, outline="black", fill="black")
    
    def display_text(self, text: str, x: int = 0, y: int = 0, font_size: str = "medium"):
        """
        Display text on the screen.
        
        Args:
            text: Text to display
            x, y: Position coordinates
            font_size: "small", "medium", "large", or "xlarge"
        """
        if not self.is_available():
            print(f"OLED not available, would display: {text}")
            return
        
        font = {
            "small": self.font_small,
            "medium": self.font_medium,
            "large": self.font_large,
            "xlarge": self.font_xlarge
        }.get(font_size, self.font_medium)
        
        with canvas(self.device) as draw:
            draw.text((x, y), text, font=font, fill="white")
    
    def display_multiline_text(self, lines: List[str], font_size: str = "small"):
        """
        Display multiple lines of text.
        
        Args:
            lines: List of text lines
            font_size: "small", "medium", "large", or "xlarge"
        """
        if not self.is_available():
            print(f"OLED not available, would display: {lines}")
            return
        
        font = {
            "small": self.font_small,
            "medium": self.font_medium,
            "large": self.font_large,
            "xlarge": self.font_xlarge
        }.get(font_size, self.font_small)
        
        with canvas(self.device) as draw:
            line_height = 10 if font_size == "small" else 12 if font_size == "medium" else 14 if font_size == "large" else 18
            
            for i, line in enumerate(lines[:4]):  # Max 4 lines for 32px height
                y = i * line_height
                draw.text((0, y), line, font=font, fill="white")
    
    def display_status(self, title: str, status: str, additional_info: Optional[str] = None):
        """
        Display status information in a formatted way.
        
        Args:
            title: Main title
            status: Status message
            additional_info: Optional additional information
        """
        if not self.is_available():
            print(f"OLED not available, would display status: {title} - {status}")
            return
        
        with canvas(self.device) as draw:
            # Title in larger font
            draw.text((0, 0), title[:16], font=self.font_medium, fill="white")
            
            # Status in smaller font
            draw.text((0, 12), status[:21], font=self.font_small, fill="white")
            
            # Additional info if provided
            if additional_info:
                draw.text((0, 22), additional_info[:21], font=self.font_small, fill="white")
    
    def display_time_and_status(self, status: str = "Ready"):
        """Display current time and status."""
        if not self.is_available():
            print(f"OLED not available, would display time and status: {status}")
            return
        
        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        date_str = now.strftime("%m/%d")
        
        with canvas(self.device) as draw:
            # Time in large font
            draw.text((0, 0), time_str, font=self.font_medium, fill="white")
            
            # Date in small font
            draw.text((80, 2), date_str, font=self.font_small, fill="white")
            
            # Status
            draw.text((0, 16), f"Status: {status}", font=self.font_small, fill="white")
    
    def display_progress_bar(self, percentage: int, label: str = "Progress"):
        """
        Display a progress bar.
        
        Args:
            percentage: Progress percentage (0-100)
            label: Label for the progress bar
        """
        if not self.is_available():
            print(f"OLED not available, would display progress: {label} {percentage}%")
            return
        
        with canvas(self.device) as draw:
            # Label
            draw.text((0, 0), label, font=self.font_small, fill="white")
            
            # Progress bar outline
            bar_x, bar_y, bar_width, bar_height = 0, 12, 128, 10
            draw.rectangle((bar_x, bar_y, bar_x + bar_width, bar_y + bar_height), outline="white")
            
            # Progress bar fill
            fill_width = int((percentage / 100.0) * (bar_width - 2))
            if fill_width > 0:
                draw.rectangle((bar_x + 1, bar_y + 1, bar_x + 1 + fill_width, bar_y + bar_height - 1), fill="white")
            
            # Percentage text
            percentage_text = f"{percentage}%"
            draw.text((0, 24), percentage_text, font=self.font_small, fill="white")
    
    def display_network_info(self, ip_address: str = "N/A"):
        """Display network information."""
        if not self.is_available():
            print(f"OLED not available, would display network info: IP {ip_address}")
            return
        
        with canvas(self.device) as draw:
            draw.text((0, 0), "Network Info", font=self.font_medium, fill="white")
            draw.text((0, 12), f"IP: {ip_address}", font=self.font_small, fill="white")
            draw.text((0, 22), f"Host: label.local", font=self.font_small, fill="white")
    
    def test_display(self):
        """Run a test sequence to verify the display is working."""
        if not self.is_available():
            print("OLED display not available for testing")
            return
        
        print("Running OLED display test...")
        
        # Test 1: Clear display
        self.clear()
        time.sleep(1)
        
        # Test 2: Simple text
        self.display_text("Hello OLED!", 0, 10, "medium")
        time.sleep(2)
        
        # Test 3: Multi-line text
        self.display_multiline_text([
            "Line 1: Hello",
            "Line 2: World",
            "Line 3: From Pi",
            "Line 4: OLED Test"
        ])
        time.sleep(2)
        
        # Test 4: Status display
        self.display_status("Label Printer", "Online", "Ready to print")
        time.sleep(2)
        
        # Test 5: Time and status
        self.display_time_and_status("Testing...")
        time.sleep(2)
        
        # Test 6: Progress bar
        for i in range(0, 101, 10):
            self.display_progress_bar(i, "Testing")
            time.sleep(0.5)
        
        # Test 7: Network info
        self.display_network_info("192.168.1.100")
        time.sleep(2)
        
        print("OLED display test completed!")


# Global instance
oled = None

def initialize_oled(i2c_port: int = 1, i2c_address: int = 0x3c) -> OLEDDisplay:
    """Initialize the global OLED display instance."""
    global oled
    oled = OLEDDisplay(i2c_port, i2c_address)
    return oled

def get_oled() -> Optional[OLEDDisplay]:
    """Get the global OLED display instance."""
    return oled

if __name__ == "__main__":
    # Test the display when run directly
    display = OLEDDisplay()
    display.test_display()
