import io
import os
import subprocess
from flask import Flask, render_template, request, Response, redirect, url_for
from urllib.parse import quote
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from typing import Optional
from typing import Dict, Tuple, List


app = Flask(__name__, static_folder="static", template_folder="templates")
def _list_fonts() -> Tuple[Dict[str, str], List[Tuple[str, str]]]:
    """Return (key->path map, list of (key, label)) for bundled fonts.
    Only files within static/fonts are exposed to avoid arbitrary paths.
    """
    fonts_dir = os.path.join(app.static_folder, "fonts")
    key_to_path: Dict[str, str] = {}
    items: List[Tuple[str, str]] = []
    if os.path.isdir(fonts_dir):
        for name in sorted(os.listdir(fonts_dir)):
            if name.lower().endswith((".ttf", ".otf")):
                key = os.path.splitext(name)[0]
                path = os.path.join(fonts_dir, name)
                key_to_path[key] = path
                # Make a nicer label
                label = key.replace("_", " ").replace("-", " ")
                items.append((key, label))
    return key_to_path, items


def _resolve_font_path(key: Optional[str]) -> Optional[str]:
    if not key:
        return None
    key_to_path, _ = _list_fonts()
    return key_to_path.get(key)


def _find_font_by_prefix(prefixes: List[str]) -> Optional[str]:
    fonts_dir = os.path.join(app.static_folder, "fonts")
    if not os.path.isdir(fonts_dir):
        return None
    matches: List[str] = []
    for name in os.listdir(fonts_dir):
        low = name.lower()
        if not low.endswith((".ttf", ".otf")):
            continue
        if any(low.startswith(p.lower()) for p in prefixes):
            matches.append(name)
    if not matches:
        return None
    matches.sort(key=lambda n: (0 if "regular" in n.lower() else 1, n.lower()))
    return os.path.join(fonts_dir, matches[0])



class Renderer:
    MM_TO_IN = 0.0393701
    DPI = 300

    def __init__(self, size_mm=(36, 89)):
        w_px = int(size_mm[1] * self.MM_TO_IN * self.DPI)
        h_px = int(size_mm[0] * self.MM_TO_IN * self.DPI)
        self.size = (w_px, h_px)
        self.img = Image.new("RGB", self.size, color="white")
        self.draw = ImageDraw.Draw(self.img)

    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int):
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
            lines.append(line)
        return lines

    def render_text_center(self, text: str, font_size: int, font_path: Optional[str] = None):
        try:
            candidates = []
            if font_path:
                candidates.append(font_path)
            try:
                static_fonts = os.path.join(app.static_folder, "fonts")
            except Exception:
                static_fonts = None
            if static_fonts:
                candidates.append(os.path.join(static_fonts, "LabelSans.ttf"))
                candidates.append(os.path.join(static_fonts, "DejaVuSans.ttf"))
            candidates.append("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")

            chosen = None
            for c in candidates:
                if c and os.path.exists(c):
                    chosen = c
                    break
            if chosen:
                font = ImageFont.truetype(chosen, font_size)
            else:
                font = ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()

        padding = int(self.size[0] * 0.04)
        lines = self._wrap_text(text, font, self.size[0] - padding * 2)

        line_heights = []
        for ln in lines:
            bbox = self.draw.textbbox((0, 0), ln, font=font)
            line_heights.append(bbox[3] - bbox[1])
        total_h = sum(line_heights) + (len(lines) - 1) * int(font_size * 0.15)

        y = (self.size[1] - total_h) // 2 - 25
        for i, ln in enumerate(lines):
            w = int(self.draw.textlength(ln, font=font))
            x = (self.size[0] - w) // 2
            self.draw.text((x, y), ln, fill="black", font=font)
            y += line_heights[i] + int(font_size * 0.15)

    def to_png_bytes(self) -> bytes:
        buf = io.BytesIO()
        self.img.save(buf, format="PNG")
        return buf.getvalue()

    def render_time_vertical(self, font_path: Optional[str] = None, font_size: int = 24, side: str = "right", offset_lines: int = 2):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        try:
            if font_path and os.path.exists(font_path):
                font = ImageFont.truetype(font_path, font_size)
            else:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()

        # Measure with potential negative bearings
        tmp = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
        dr = ImageDraw.Draw(tmp)
        bbox = dr.textbbox((0, 0), ts, font=font)
        w = max(1, bbox[2] - bbox[0])
        h = max(1, bbox[3] - bbox[1])
        pad = max(4, (font_size + 1) // 3)

        # Draw onto padded surface compensating for negative bbox origin
        txt = Image.new("RGBA", (w + pad * 2, h + pad * 2), (255, 255, 255, 0))
        dr2 = ImageDraw.Draw(txt)
        dr2.text((pad - bbox[0], pad - bbox[1]), ts, fill=(0, 0, 0, 255), font=font)

        # Rotate and crop to content to avoid any residual transparent borders
        rot = txt.rotate(90, expand=True)
        crop_box = rot.getbbox()
        if crop_box:
            rot = rot.crop(crop_box)

        margin = max(6, int(self.size[0] * 0.01))
        extra = max(0, offset_lines * font_size)  # shift left by N line-heights
        if side == "left":
            x = max(margin, margin + extra)
        else:
            x = max(margin, self.size[0] - rot.width - margin - extra)
        y = (self.size[1] - rot.height) // 2
        self.img.paste(rot, (x, y), rot)


@app.route("/")
def index():
    text = request.args.get("text", "")
    try:
        size = int(request.args.get("size", "144") or "144")
    except ValueError:
        size = 56
    query = f"?text={quote(text or '')}"
    preview_url = url_for("api_preview", size=size) + query
    status = request.args.get("status", "")
    return render_template(
        "index.html",
        text=text,
        size=size,
        preview_url=preview_url,
        status=status,
    )

@app.get("/api/preview/<int:size>/")
def api_preview(size: int):
    text = request.args.get("text", "").strip()
    # Default fonts: Ubuntu for main, B612 for timestamp
    font_path = _find_font_by_prefix(["ubuntu"]) or _resolve_font_path(None)
    time_font_path = _find_font_by_prefix(["b612"]) or font_path
    r = Renderer()
    r.render_text_center(text or "", size, font_path=font_path)
    r.render_time_vertical(font_path=time_font_path, font_size=24, side="right")
    png = r.to_png_bytes()
    return Response(png, mimetype="image/png")


def _print_via_lp(png_bytes: bytes) -> tuple[int, str]:
    tmp_path = "/tmp/pilabel.png"
    with open(tmp_path, "wb") as f:
        f.write(png_bytes)
    printer = os.environ.get("PRINTER", os.environ.get("PILABEL_PRINTER", "dymo450"))
    media = os.environ.get("PILABEL_MEDIA", "w102h252")  # 36x89mm ≈ 102x252pt
    copies = int(os.environ.get("PILABEL_COPIES", "2") or "2")

    img_list = [tmp_path] * max(1, copies)
    convert_args = [
        "convert",
        *img_list,
        "-units",
        "PixelsPerInch",
        "-density",
        "300",
        "-compress",
        "zip",
        "pdf:-",
    ]
    lp_args = [
        "lp",
        "-d",
        printer,
        "-o",
        f"PageSize={media}",
        "-o",
        "Resolution=300dpi",
        "-o",
        "DymoPrintQuality=Text",
        "-o",
        "fit-to-page",
        "-t",
        "label.pdf",
    ]
    try:
        p1 = subprocess.Popen(convert_args, stdout=subprocess.PIPE)
        proc = subprocess.run(lp_args, stdin=p1.stdout, capture_output=True, check=False)
        if p1.stdout:
            p1.stdout.close()
        p1.wait()
        try:
            stdout = (proc.stdout.decode("utf-8", errors="ignore") if isinstance(proc.stdout, (bytes, bytearray)) else (proc.stdout or ""))
            stderr = (proc.stderr.decode("utf-8", errors="ignore") if isinstance(proc.stderr, (bytes, bytearray)) else (proc.stderr or ""))
            print(
                "convert args: "
                + " ".join(convert_args)
                + "\nlp args: "
                + " ".join(lp_args)
                + f"\nstdout: {stdout.strip()}\nstderr: {stderr.strip()}"
            )
        except Exception:
            stdout = ""
            stderr = ""
        out = (stdout or "") + (stderr or "")
        return proc.returncode, out
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


# Remote print support removed; always use local CUPS via lp.


@app.get("/printed")
def printed():
    return render_template("printed.html")


@app.post("/print")
def print_form():
    text = request.form.get("text", "").strip()
    try:
        size = int(request.form.get("size", "144") or "144")
    except ValueError:
        size = 56
    font_path = _find_font_by_prefix(["ubuntu"]) or _resolve_font_path(None)
    time_font_path = _find_font_by_prefix(["b612"]) or font_path

    r = Renderer()
    r.render_text_center(text or "", size, font_path=font_path)
    r.render_time_vertical(font_path=time_font_path, font_size=24, side="right")
    png = r.to_png_bytes()

    code, out = _print_via_lp(png)

    success = (code == 0)
    status = "Printed" if success else f"Print failed ({code}): {(out or '').splitlines()[0]}"
    try:
        print(f"print_form: size={size}, font_main={os.path.basename(font_path) if font_path else 'auto'}, font_time={os.path.basename(time_font_path) if time_font_path else 'auto'}, bytes={len(png)}, exit={code}, msg={(out or '').strip()[:200]}")
    except Exception:
        pass
    return redirect(url_for("printed"))


def main():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))


if __name__ == "__main__":
    main()
