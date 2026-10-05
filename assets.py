import os
from PIL import Image, ImageDraw, ImageTk
from config import (
    BASE_DIR,
    BODY_FILE,
    HARD_EDGES,
    HEAD_FILE,
    IMAGE_DIR,
    ROTATE_BODY,
    ROTATE_HEAD,
    SEGMENT_SIZE,
    TAIL_FILE,
)

RESAMPLING = getattr(Image, "Resampling", Image)
LANCZOS = RESAMPLING.LANCZOS
BICUBIC = RESAMPLING.BICUBIC


def harden(img):
    r, g, b, a = img.split()
    a = Image.eval(a, lambda v: 255 if v >= 128 else 0)
    img.putalpha(a)
    return img


def fallback_image(color):
    img = Image.new("RGBA", (SEGMENT_SIZE, SEGMENT_SIZE), (0, 0, 0, 0))
    ImageDraw.Draw(img).ellipse(
        (2, 2, SEGMENT_SIZE - 3, SEGMENT_SIZE - 3),
        fill=color,
        outline=(27, 77, 43, 255),
        width=2,
    )
    return img


def load_image(filename, fallback_color):
    if filename:
        path = os.path.join(BASE_DIR, IMAGE_DIR, filename)
        if os.path.exists(path):
            img = Image.open(path).convert("RGBA")
            return img.resize((SEGMENT_SIZE, SEGMENT_SIZE), LANCZOS)
    return fallback_image(fallback_color)


_rotation_cache = {}
_photo_cache = {}


def precalculate_rotations(name, base_img, allow_rotate):
    _rotation_cache[name] = [None] * 360
    _photo_cache[name] = [None] * 360

    if not allow_rotate:
        img = harden(base_img.copy()) if HARD_EDGES else base_img.copy()
        tk_img = ImageTk.PhotoImage(img)
        for deg in range(360):
            _rotation_cache[name][deg] = img
            _photo_cache[name][deg] = tk_img
        return

    for deg in range(360):
        rotated = base_img.rotate(deg, resample=BICUBIC) if deg != 0 else base_img.copy()
        if HARD_EDGES:
            rotated = harden(rotated)
        _rotation_cache[name][deg] = rotated
        _photo_cache[name][deg] = ImageTk.PhotoImage(rotated)


head_img = load_image(HEAD_FILE, (120, 220, 90, 255))
body_img = load_image(BODY_FILE, (70, 170, 80, 255))
tail_img = load_image(TAIL_FILE, (70, 170, 80, 255)) if TAIL_FILE else body_img


def init_assets():
    """Must be called AFTER tk.Tk() is initialized."""
    precalculate_rotations("head", head_img, ROTATE_HEAD)
    precalculate_rotations("body", body_img, ROTATE_BODY)
    precalculate_rotations("tail", tail_img, ROTATE_BODY)


def get_base_photo(name, angle_deg):
    return _rotation_cache[name][int(angle_deg) % 360]


def get_base_tk_photo(name, angle_deg):
    return _photo_cache[name][int(angle_deg) % 360]