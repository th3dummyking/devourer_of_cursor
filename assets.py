import os
from PIL import Image, ImageDraw, ImageTk
from config import (
    BASE_DIR,
    BODY_FILE,
    BODY_FILE_2,
    HARD_EDGES,
    HEAD_FILE,
    HEAD_FILE_2,
    IMAGE_DIR,
    PHASE2_SEGMENT_SIZE,
    ROTATE_BODY,
    ROTATE_HEAD,
    SEGMENT_SIZE,
    TAIL_FILE,
    TAIL_FILE_2,
)

RESAMPLING = getattr(Image, "Resampling", Image)
LANCZOS = RESAMPLING.LANCZOS
BICUBIC = RESAMPLING.BICUBIC


def harden(img):
    r, g, b, a = img.split()
    a = Image.eval(a, lambda v: 255 if v >= 128 else 0)
    img.putalpha(a)
    return img


def fallback_image(size, color):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(img).ellipse(
        (2, 2, size - 3, size - 3),
        fill=color,
        outline=(27, 77, 43, 255),
        width=2,
    )
    return img


def _open_image(filename, size):
    if filename:
        path = os.path.join(BASE_DIR, IMAGE_DIR, filename)
        if os.path.exists(path):
            img = Image.open(path).convert("RGBA")
            return img.resize((size, size), LANCZOS)
    return None


def load_image(filename, size, fallback_color, fallback_filename=None):
    """Loads `filename` at `size`. If missing, tries `fallback_filename`, then a plain circle."""
    img = _open_image(filename, size)
    if img is None and fallback_filename:
        img = _open_image(fallback_filename, size)
    return img if img is not None else fallback_image(size, fallback_color)


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


# Phase 1 images
head_img = load_image(HEAD_FILE, SEGMENT_SIZE, (120, 220, 90, 255))
body_img = load_image(BODY_FILE, SEGMENT_SIZE, (70, 170, 80, 255))
tail_img = load_image(TAIL_FILE, SEGMENT_SIZE, (70, 170, 80, 255)) if TAIL_FILE else body_img

# Phase 2 images (head_2 / body_2 / tail_2). Missing files fall back to the phase 1 image, scaled up.
head_img2 = load_image(HEAD_FILE_2, PHASE2_SEGMENT_SIZE, (220, 90, 90, 255), fallback_filename=HEAD_FILE)
body_img2 = load_image(BODY_FILE_2, PHASE2_SEGMENT_SIZE, (170, 70, 70, 255), fallback_filename=BODY_FILE)
tail_img2 = (
    load_image(TAIL_FILE_2, PHASE2_SEGMENT_SIZE, (170, 70, 70, 255), fallback_filename=TAIL_FILE)
    if (TAIL_FILE_2 or TAIL_FILE)
    else body_img2
)


def init_assets():
    """Must be called AFTER tk.Tk() is initialized."""
    precalculate_rotations("head", head_img, ROTATE_HEAD)
    precalculate_rotations("body", body_img, ROTATE_BODY)
    precalculate_rotations("tail", tail_img, ROTATE_BODY)
    # Phase 2 sets use the same names with a "2" suffix
    precalculate_rotations("head2", head_img2, ROTATE_HEAD)
    precalculate_rotations("body2", body_img2, ROTATE_BODY)
    precalculate_rotations("tail2", tail_img2, ROTATE_BODY)


def get_base_photo(name, angle_deg):
    return _rotation_cache[name][int(angle_deg) % 360]


def get_base_tk_photo(name, angle_deg):
    return _photo_cache[name][int(angle_deg) % 360]
