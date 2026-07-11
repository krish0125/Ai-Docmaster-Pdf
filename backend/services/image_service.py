"""Image Tools Service — Phase 7.

resize, thumbnail, convert format, apply filters (grayscale/sepia/blur/sharpen),
background removal (rembg if available), upscaling (ESRGAN-lite / PIL fallback).
"""

from __future__ import annotations
import os
import uuid
from PIL import Image, ImageFilter, ImageEnhance, ImageOps


def _out(upload_folder: str, suffix: str) -> tuple[str, str]:
    fname = f"img_{uuid.uuid4().hex}{suffix}"
    path  = os.path.join(upload_folder, fname)
    os.makedirs(upload_folder, exist_ok=True)
    return fname, path


def _load(image_path: str) -> Image.Image:
    return Image.open(image_path).convert('RGBA')


# ───────────────────────────────────────────────────────────────────────────
# Resize
# ───────────────────────────────────────────────────────────────────────────

def resize_image(image_path: str, width: int, height: int,
                 keep_ratio: bool, upload_folder: str) -> tuple[str, str]:
    """Resize an image to exactly *width* × *height* (or preserving ratio)."""
    img = _load(image_path).convert('RGB')
    if keep_ratio:
        img.thumbnail((width, height), Image.LANCZOS)
    else:
        img = img.resize((width, height), Image.LANCZOS)
    ext = os.path.splitext(image_path)[-1].lower() or '.jpg'
    fname, fpath = _out(upload_folder, ext)
    img.save(fpath)
    return fname, fpath


def create_thumbnail(image_path: str, size: int, upload_folder: str) -> tuple[str, str]:
    """Create a square thumbnail (cropped centre + resized)."""
    img = _load(image_path).convert('RGB')
    # Centre-crop to square first
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top  = (h - side) // 2
    img  = img.crop((left, top, left + side, top + side))
    img  = img.resize((size, size), Image.LANCZOS)
    fname, fpath = _out(upload_folder, '.jpg')
    img.save(fpath, 'JPEG')
    return fname, fpath


# ───────────────────────────────────────────────────────────────────────────
# Format Conversion
# ───────────────────────────────────────────────────────────────────────────

def convert_format(image_path: str, target_fmt: str,
                   upload_folder: str) -> tuple[str, str]:
    """Convert image to *target_fmt* ('jpg', 'png', 'webp', 'bmp', 'tiff')."""
    fmt = target_fmt.lower().lstrip('.')
    pil_fmt = {'jpg': 'JPEG', 'jpeg': 'JPEG', 'png': 'PNG',
                'webp': 'WEBP', 'bmp': 'BMP', 'tiff': 'TIFF',
                'gif': 'GIF'}.get(fmt, fmt.upper())
    img = _load(image_path)
    if pil_fmt == 'JPEG':
        img = img.convert('RGB')
    fname, fpath = _out(upload_folder, f'.{fmt}')
    img.save(fpath, pil_fmt)
    return fname, fpath


# ───────────────────────────────────────────────────────────────────────────
# Filters
# ───────────────────────────────────────────────────────────────────────────

def apply_filter(image_path: str, filter_name: str,
                 upload_folder: str) -> tuple[str, str]:
    """Apply a named filter to an image.

    Supported: grayscale, sepia, blur, sharpen, edge, emboss, invert,
               brightness+, brightness-, contrast+, contrast-.
    """
    img = Image.open(image_path).convert('RGB')
    fn  = filter_name.lower()

    if fn == 'grayscale':
        img = ImageOps.grayscale(img).convert('RGB')
    elif fn == 'sepia':
        gray = ImageOps.grayscale(img)
        img  = gray.convert('RGB')
        px   = img.load()
        w, h = img.size
        for y in range(h):
            for x in range(w):
                r, g, b = px[x, y]
                tr = min(255, int(r * 0.393 + g * 0.769 + b * 0.189))
                tg = min(255, int(r * 0.349 + g * 0.686 + b * 0.168))
                tb = min(255, int(r * 0.272 + g * 0.534 + b * 0.131))
                px[x, y] = (tr, tg, tb)
    elif fn == 'blur':
        img = img.filter(ImageFilter.GaussianBlur(radius=3))
    elif fn == 'sharpen':
        img = img.filter(ImageFilter.SHARPEN)
    elif fn == 'edge':
        img = img.filter(ImageFilter.FIND_EDGES)
    elif fn == 'emboss':
        img = img.filter(ImageFilter.EMBOSS)
    elif fn == 'invert':
        img = ImageOps.invert(img)
    elif fn == 'brightness+':
        img = ImageEnhance.Brightness(img).enhance(1.5)
    elif fn == 'brightness-':
        img = ImageEnhance.Brightness(img).enhance(0.6)
    elif fn == 'contrast+':
        img = ImageEnhance.Contrast(img).enhance(1.8)
    elif fn == 'contrast-':
        img = ImageEnhance.Contrast(img).enhance(0.5)
    elif fn == 'saturation+':
        img = ImageEnhance.Color(img).enhance(1.8)
    elif fn == 'saturation-':
        img = ImageEnhance.Color(img).enhance(0.3)
    else:
        raise ValueError(f"Unknown filter: {filter_name}")

    fname, fpath = _out(upload_folder, '.png')
    img.save(fpath)
    return fname, fpath


# ───────────────────────────────────────────────────────────────────────────
# Background Removal
# ───────────────────────────────────────────────────────────────────────────

def remove_background(image_path: str, upload_folder: str) -> tuple[str, str]:
    """Remove the background using rembg (AI-based).
    Falls back to a simple white-tolerance crop if rembg is unavailable.
    """
    fname, fpath = _out(upload_folder, '.png')
    try:
        from rembg import remove
        from PIL import Image as PILImage
        inp = PILImage.open(image_path)
        out = remove(inp)
        out.save(fpath)
        return fname, fpath
    except ImportError:
        pass

    # Fallback: flood-fill from corners (simple tolerance-based)
    img = Image.open(image_path).convert('RGBA')
    data = img.getdata()
    new_data = []
    bg_r, bg_g, bg_b, _ = data[0]
    tol = 40
    for r, g, b, a in data:
        if abs(r - bg_r) < tol and abs(g - bg_g) < tol and abs(b - bg_b) < tol:
            new_data.append((0, 0, 0, 0))
        else:
            new_data.append((r, g, b, a))
    img.putdata(new_data)
    img.save(fpath)
    return fname, fpath


# ───────────────────────────────────────────────────────────────────────────
# Upscaling
# ───────────────────────────────────────────────────────────────────────────

def upscale_image(image_path: str, scale: int, upload_folder: str) -> tuple[str, str]:
    """Upscale an image by *scale* factor.

    Uses PIL LANCZOS (high quality bicubic-like) resampling.
    For real AI upscaling install: pip install super-image
    """
    img = Image.open(image_path).convert('RGB')
    w, h = img.size
    img = img.resize((w * scale, h * scale), Image.LANCZOS)
    fname, fpath = _out(upload_folder, '.png')
    img.save(fpath)
    return fname, fpath


# ───────────────────────────────────────────────────────────────────────────
# Crop
# ───────────────────────────────────────────────────────────────────────────

def crop_image(image_path: str, left: int, top: int, right: int, bottom: int,
               upload_folder: str) -> tuple[str, str]:
    """Crop an image to the specified pixel bounding box."""
    img = Image.open(image_path).convert('RGB')
    w, h = img.size
    box = (
        max(0, left), max(0, top),
        min(w, right), min(h, bottom)
    )
    img = img.crop(box)
    fname, fpath = _out(upload_folder, '.png')
    img.save(fpath)
    return fname, fpath


# ───────────────────────────────────────────────────────────────────────────
# Rotate / Flip
# ───────────────────────────────────────────────────────────────────────────

def rotate_image(image_path: str, angle: int, upload_folder: str) -> tuple[str, str]:
    img = Image.open(image_path).convert('RGB')
    img = img.rotate(-angle, expand=True)   # PIL rotates CCW; negate for CW
    fname, fpath = _out(upload_folder, '.png')
    img.save(fpath)
    return fname, fpath


def flip_image(image_path: str, direction: str, upload_folder: str) -> tuple[str, str]:
    """Flip image horizontally ('h') or vertically ('v')."""
    img = Image.open(image_path).convert('RGB')
    if direction.lower() in ('h', 'horizontal'):
        img = ImageOps.mirror(img)
    else:
        img = ImageOps.flip(img)
    fname, fpath = _out(upload_folder, '.png')
    img.save(fpath)
    return fname, fpath


# ───────────────────────────────────────────────────────────────────────────
# Add Text Watermark to Image
# ───────────────────────────────────────────────────────────────────────────

def add_text_watermark(image_path: str, text: str, opacity: int,
                       upload_folder: str) -> tuple[str, str]:
    """Overlay semi-transparent text watermark on an image."""
    from PIL import ImageDraw, ImageFont
    img  = Image.open(image_path).convert('RGBA')
    txt  = Image.new('RGBA', img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(txt)
    w, h = img.size
    # Try a simple font; fall back to default
    try:
        font_size = max(20, w // 15)
        font = ImageFont.truetype('arial.ttf', font_size)
    except Exception:
        font = ImageFont.load_default()
    # Center the text properly
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    except AttributeError:
        tw, th = len(text) * 10, 20
    tx = max(0, (w - tw) // 2)
    ty = max(0, (h - th) // 2)
    draw.text((tx, ty), text,
              fill=(128, 128, 128, opacity), font=font)
    combined = Image.alpha_composite(img, txt)
    fname, fpath = _out(upload_folder, '.png')
    combined.convert('RGB').save(fpath)
    return fname, fpath
