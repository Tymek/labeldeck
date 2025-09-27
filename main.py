#!/usr/bin/env python3
"""
Label Printer with OLED Display
Interactive name entry and label printing system for Raspberry Pi Zero with OLED display.
"""

import os
import sys
import time
import subprocess
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from typing import Optional
import io
import termios
import tty
import locale

# Try to import OLED display functionality
try:
    from oled_display import initialize_oled, get_oled
    from luma.core.render import canvas
    OLED_AVAILABLE = True
except ImportError as e:
    print(f"OLED display not available: {e}")
    OLED_AVAILABLE = False
    canvas = None


class LabelRenderer:
    """Renders labels for printing."""
    
    MM_TO_IN = 0.0393701
    DPI = 300

    def __init__(self, size_mm=(36, 89)):
        """Initialize renderer with label size in millimeters."""
        w_px = int(size_mm[1] * self.MM_TO_IN * self.DPI)
        h_px = int(size_mm[0] * self.MM_TO_IN * self.DPI)
        self.size = (w_px, h_px)
        self.img = Image.new("RGB", self.size, color="white")
        self.draw = ImageDraw.Draw(self.img)

    def _find_font(self, prefixes=None, size=20):
        """Find and load a suitable font."""
        if prefixes is None:
            prefixes = ["ubuntu", "dejavu", "liberation"]
        
        candidates = []
        
        # Static fonts from project
        static_fonts = "static/fonts"
        if os.path.exists(static_fonts):
            for name in os.listdir(static_fonts):
                if name.lower().endswith((".ttf", ".otf")):
                    candidates.append(os.path.join(static_fonts, name))
        
        # System fonts
        system_font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
        ]
        candidates.extend(system_font_paths)
        
        # Find best match
        for prefix in prefixes:
            for path in candidates:
                if prefix.lower() in os.path.basename(path).lower():
                    try:
                        return ImageFont.truetype(path, size)
                    except (OSError, IOError):
                        continue
        
        # Try any available font
        for path in candidates:
            try:
                if os.path.exists(path):
                    return ImageFont.truetype(path, size)
            except (OSError, IOError):
                continue
        
        # Fallback to default font
        return ImageFont.load_default()

    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int):
        """Wrap text to fit within max_width."""
        lines = []
        for paragraph in text.split("\n"):
            words = paragraph.split(" ")
            line = ""
            for word in words:
                test = (line + (" " if line else "") + word).strip()
                if self.draw.textlength(test, font=font) <= max_width:
                    line = test
                else:
                    if line:
                        lines.append(line)
                    line = word
            if line:
                lines.append(line)
        return lines

    def render_name_label(self, name: str, font_size: int = 144):
        """Render a name label."""
        font = self._find_font(["ubuntu", "dejavu"], font_size)
        
        # Clear the image
        self.draw.rectangle([(0, 0), self.size], fill="white")
        
        padding = int(self.size[0] * 0.04)
        lines = self._wrap_text(name, font, self.size[0] - padding * 2)

        # Calculate total height
        line_heights = []
        for ln in lines:
            bbox = self.draw.textbbox((0, 0), ln, font=font)
            line_heights.append(bbox[3] - bbox[1])
        
        line_spacing = int(font_size * 0.15)
        total_h = sum(line_heights) + (len(lines) - 1) * line_spacing

        # Center vertically
        y = (self.size[1] - total_h) // 2 - 25
        
        # Draw each line centered horizontally
        for i, ln in enumerate(lines):
            w = int(self.draw.textlength(ln, font=font))
            x = (self.size[0] - w) // 2
            self.draw.text((x, y), ln, fill="black", font=font)
            y += line_heights[i] + line_spacing

        # Add timestamp in corner
        self._add_timestamp()

    def _add_timestamp(self):
        """Add timestamp to the label."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        font = self._find_font(["b612", "dejavu"], 32)
        
        # Position in bottom right
        bbox = self.draw.textbbox((0, 0), timestamp, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        
        x = self.size[0] - w - 10
        y = self.size[1] - h - 10
        
        self.draw.text((x, y), timestamp, fill="black", font=font)

    def to_png_bytes(self) -> bytes:
        """Convert rendered image to PNG bytes."""
        buf = io.BytesIO()
        self.img.save(buf, format="PNG")
        return buf.getvalue()

    def save_png(self, path: str):
        """Save rendered image as PNG file."""
        self.img.save(path, format="PNG")


def print_label(png_bytes: bytes, copies: int = 1) -> tuple[int, str]:
    """Print label using CUPS via lp command."""
    tmp_path = "/tmp/pilabel.png"
    
    try:
        # Save PNG to temporary file
        with open(tmp_path, "wb") as f:
            f.write(png_bytes)
        
        # Get printer configuration from environment
        printer = os.environ.get("PRINTER", os.environ.get("PILABEL_PRINTER", "dymo450"))
        media = os.environ.get("PILABEL_MEDIA", "w102h252")  # 36x89mm ≈ 102x252pt
        
        # Create list of images for copies
        img_list = [tmp_path] * max(1, copies)
        
        # Convert to PDF with ImageMagick
        convert_args = [
            "convert",
            *img_list,
            "-units", "PixelsPerInch",
            "-density", "300",
            "-compress", "zip",
            "pdf:-",
        ]
        
        # Print with lp
        lp_args = [
            "lp",
            "-d", printer,
            "-o", f"PageSize={media}",
            "-o", "Resolution=300dpi",
            "-o", "DymoPrintQuality=Text",
            "-o", "fit-to-page",
            "-t", "label.pdf",
        ]
        
        # Execute print pipeline
        p1 = subprocess.Popen(convert_args, stdout=subprocess.PIPE)
        proc = subprocess.run(lp_args, stdin=p1.stdout, capture_output=True, check=False)
        
        if p1.stdout:
            p1.stdout.close()
        p1.wait()
        
        # Get output for debugging
        stdout = proc.stdout.decode("utf-8", errors="ignore") if proc.stdout else ""
        stderr = proc.stderr.decode("utf-8", errors="ignore") if proc.stderr else ""
        
        output = (stdout + stderr).strip()
        
        print(f"Print command executed:")
        print(f"Convert: {' '.join(convert_args)}")
        print(f"LP: {' '.join(lp_args)}")
        print(f"Output: {output}")
        
        return proc.returncode, output
        
    except Exception as e:
        return 1, str(e)
    
    finally:
        # Clean up temporary file
        try:
            os.remove(tmp_path)
        except Exception:
            pass


class LabelPrinterApp:
    """Main application for interactive label printing."""
    
    def __init__(self):
        self.oled = None
        self.renderer = LabelRenderer()
        
        # Initialize OLED display
        if OLED_AVAILABLE:
            try:
                self.oled = initialize_oled()
                if self.oled and self.oled.is_available():
                    print("OLED display initialized successfully")
                    self.oled.display_status("Label Printer", "Starting up...", "Please wait")
                    time.sleep(2)
                else:
                    print("OLED display not available")
                    self.oled = None
            except Exception as e:
                print(f"Failed to initialize OLED: {e}")
                self.oled = None
        else:
            print("OLED support not available")

    def display_message(self, message: str, line2: str = "", line3: str = ""):
        """Display message on OLED if available, otherwise print."""
        if self.oled and self.oled.is_available():
            lines = [message]
            if line2:
                lines.append(line2)
            if line3:
                lines.append(line3)
            self.oled.display_multiline_text(lines)
        else:
            print(message)
            if line2:
                print(line2)
            if line3:
                print(line3)

    def display_status(self, title: str, status: str, info: str = ""):
        """Display status on OLED if available."""
        if self.oled and self.oled.is_available():
            self.oled.display_status(title, status, info)
        else:
            print(f"{title}: {status}")
            if info:
                print(f"  {info}")

    def get_name_input(self) -> str:
        """Get name input from user with real-time display, supporting Polish characters."""
        self.display_message("Enter name:", "", "")
        
        name = ""
        
        # Ensure UTF-8 encoding
        import locale
        try:
            locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
        except locale.Error:
            try:
                locale.setlocale(locale.LC_ALL, 'C.UTF-8')
            except locale.Error:
                pass  # Use system default
        
        # Try character-by-character input, fallback to regular input
        try:
            # Save original terminal settings
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            
            # Set terminal to raw mode for character input
            tty.setraw(fd)
            
            while True:
                # Update display with current input
                if self.oled and self.oled.is_available():
                    # Use canvas for smoother display updates
                    if canvas:
                        with canvas(self.oled.device) as draw:
                            # Title at top
                            draw.text((0, 0), "Enter name:", font=self.oled.font_small, fill="white")
                            # Current input in large font
                            display_text = name if name else "_"
                            draw.text((0, 12), display_text, font=self.oled.font_large, fill="white")
                    else:
                        # Fallback to individual calls
                        self.oled.clear()
                        self.oled.display_text("Enter name:", x=0, y=0, font_size="small")
                        display_text = name if name else "_"
                        self.oled.display_text(display_text, x=0, y=12, font_size="large")
                else:
                    # Clear line and show current input
                    print(f"\rEnter name: {name}_", end="", flush=True)
                
                # Read single character or UTF-8 sequence
                try:
                    # Read first byte
                    char = sys.stdin.read(1)
                    if not char:
                        continue
                        
                    # Handle special keys first
                    char_code = ord(char)
                    if char_code == 13 or char_code == 10:  # Enter key
                        break
                    elif char_code == 127 or char_code == 8:  # Backspace
                        if name:
                            # Handle UTF-8 characters properly when backspacing
                            try:
                                name = name[:-1]
                                # If we get a decode error, we might have cut in middle of UTF-8 char
                                name.encode('utf-8')
                            except UnicodeEncodeError:
                                # Cut one more character to get to valid UTF-8 boundary
                                if name:
                                    name = name[:-1]
                        continue
                    elif char_code == 3:  # Ctrl+C
                        raise KeyboardInterrupt
                    
                    # Handle UTF-8 multi-byte characters
                    if char_code < 128:
                        # ASCII character
                        if char_code >= 32:  # Printable ASCII
                            name += char
                    else:
                        # Multi-byte UTF-8 character
                        # Determine how many bytes we need to read
                        if char_code < 0xC0:
                            # Invalid UTF-8 start byte, skip
                            continue
                        elif char_code < 0xE0:
                            # 2-byte sequence
                            char += sys.stdin.read(1)
                        elif char_code < 0xF0:
                            # 3-byte sequence (covers most Polish characters)
                            char += sys.stdin.read(2)
                        elif char_code < 0xF8:
                            # 4-byte sequence
                            char += sys.stdin.read(3)
                        else:
                            # Invalid, skip
                            continue
                        
                        # Try to decode the UTF-8 sequence
                        try:
                            decoded_char = char.decode('utf-8')
                            # Add the character if it's printable
                            if decoded_char.isprintable():
                                name += decoded_char
                        except UnicodeDecodeError:
                            # Skip invalid UTF-8 sequences
                            continue
                            
                except (UnicodeDecodeError, IndexError):
                    # Handle any encoding issues gracefully
                    continue
                    
        except (KeyboardInterrupt, OSError, AttributeError):
            # Fallback to regular input if terminal control fails
            try:
                # Restore terminal settings if possible
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            except:
                pass
            
            if isinstance(sys.exc_info()[1], KeyboardInterrupt):
                name = ""
            else:
                # Use regular input as fallback
                print("\nUsing standard input mode:")
                try:
                    name = input("Enter name: ").strip()
                except (EOFError, KeyboardInterrupt):
                    name = ""
        finally:
            # Restore original terminal settings
            try:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            except:
                pass
            
        # Clear the line in console output
        if not (self.oled and self.oled.is_available()):
            print()  # New line
            
        return name.strip()

    def wait_for_enter_or_cancel(self) -> bool:
        """Wait for Enter key. Returns True if Enter pressed, False for any other key or Ctrl+C."""
        try:
            # Save original terminal settings
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            
            # Set terminal to raw mode for character input
            tty.setraw(fd)
            
            # Read single character
            char = sys.stdin.read(1)
            
            # Check if it's Enter (CR or LF)
            if ord(char) == 13 or ord(char) == 10:
                return True
            else:
                # Any other key cancels
                return False
                
        except (KeyboardInterrupt, OSError, AttributeError):
            return False
        finally:
            # Restore original terminal settings
            try:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            except:
                pass

    def preview_on_oled(self, name: str):
        """Preview the name on OLED display with larger text."""
        if self.oled and self.oled.is_available():
            # Clear display first
            self.oled.clear()
            time.sleep(0.1)  # Small delay to ensure clear completes
            
            if canvas:
                # Use canvas to draw everything at once to prevent blinking
                with canvas(self.oled.device) as draw:
                    # Show full name, allow overflow to the right
                    display_name = name
                    
                    # Draw preview text with extra large font
                    font = self.oled.font_xlarge
                    draw.text((0, 4), display_name, font=font, fill="white")
                    
                    # Draw instruction at bottom with small font
                    small_font = self.oled.font_small
                    draw.text((0, 22), "Enter=print", font=small_font, fill="white")
            else:
                # Fallback to individual display calls
                self.oled.display_text(name, x=0, y=4, font_size="xlarge")
                time.sleep(0.05)
                self.oled.display_text("Enter=print", x=0, y=22, font_size="small")
        else:
            print(f"Preview: {name}")
            print("Press Enter to print, other key to cancel")

    def run_interactive_loop(self):
        """Run the main interactive loop."""
        print("Label Printer with OLED Display")
        print("=" * 40)
        
        self.display_status("Label Printer", "Ready", "Type name + Enter")
        
        while True:
            try:
                # Get name input
                name = self.get_name_input()
                
                if not name:
                    self.display_message("No name entered", "Try again...")
                    time.sleep(2)
                    self.display_status("Label Printer", "Ready", "Type name + Enter")
                    continue
                
                # Show preview
                self.preview_on_oled(name)
                
                # Wait for Enter to print, any other key to cancel
                print(f"Preview: '{name}'")
                print("Press Enter to print 2 copies, any other key to cancel:")
                
                if not self.wait_for_enter_or_cancel():
                    self.display_message("Cancelled", "Back to main menu")
                    time.sleep(1)
                    continue
                
                # Render and print label
                self.display_status("Printing...", name, "Please wait")
                
                # Render the label
                self.renderer.render_name_label(name)
                png_bytes = self.renderer.to_png_bytes()
                
                # Print 2 copies
                return_code, output = print_label(png_bytes, copies=2)
                
                if return_code == 0:
                    self.display_status("Print Success!", name, "2 copies sent")
                    print("✓ Label printed successfully!")
                else:
                    self.display_status("Print Failed", "Check printer", output[:15])
                    print(f"✗ Print failed: {output}")
                
                time.sleep(3)
                self.display_status("Label Printer", "Ready", "Type name + Enter")
                
            except KeyboardInterrupt:
                print("\nShutting down...")
                if self.oled and self.oled.is_available():
                    self.oled.display_status("Label Printer", "Goodbye!", "")
                    time.sleep(2)
                    self.oled.clear()
                break
            except Exception as e:
                print(f"Error: {e}")
                self.display_status("Error", str(e)[:12], "Try again")
                time.sleep(3)


def main():
    """Main entry point."""
    try:
        app = LabelPrinterApp()
        app.run_interactive_loop()
    except Exception as e:
        print(f"Failed to start application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
