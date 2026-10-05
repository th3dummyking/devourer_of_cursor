import json
import math
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

DEFAULT_CONFIG = {
    "segment_size": 53,
    "spacing_ratio": 0.6,
    "num_segments": 64,
    "base_speed": 10.0,
    "max_speed": 85.0,
    "slow_duration": 0.3,
    "ramp_duration": 0.5,
    "destroy_duration": 5.0,
    "deteriorate_delay": 0.4,
    "deteriorate_duration": 0.2,
    "fall_duration": 2.0,
    "break_apart": True,
    "dying_speed": 10.0,
    "dying_gravity": 20.0,
    "break_pop_force": 10.0,
    "wiggle": 5.0,
    "turn_smoothing": 0.35,
    "max_bend_deg": 35.0,
    "spawn_from_edge": "random",
    "spawn_margin": 250,
    "wander_arrive_dist": 70.0,
    "rotate_head": True,
    "rotate_body": True,
    "images_face_right": False,
    "hard_edges": True,
    "fps_ms": 16,
    "idle_fps_ms": 16,
    "idle_threshold": 1.0,
    "image_dir": "image",
    "head_file": "head.png",
    "body_file": "body.png",
    "tail_file": "tail.png",
    "dialogue_file": "dog_lines.txt",
    "speech_interval_min": 3.0,
    "speech_interval_max": 5.0,
    "speech_duration": 2.0,
    "speech_fade_duration": 1.0,
    "speech_font_family": "Arial",
    "speech_font_size": 16,
    "speech_font_weight": "bold",
    "speech_color": "#A855F7",
    "speech_offset_y": 30,
    "speech_shake_amount": 1.1
}


def load_config():
    if not os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "w") as f:
                json.dump(DEFAULT_CONFIG, f, indent=2)
        except Exception as e:
            print(f"Error creating config.json: {e}")
        return DEFAULT_CONFIG.copy()

    try:
        with open(CONFIG_PATH, "r") as f:
            cfg = json.load(f)
            merged = DEFAULT_CONFIG.copy()
            merged.update(cfg)
            return merged
    except Exception as e:
        print(f"Error loading config.json, using defaults: {e}")
        return DEFAULT_CONFIG.copy()


CFG = load_config()

# Configuration Extraction
SEGMENT_SIZE = CFG["segment_size"]
SPACING = int(SEGMENT_SIZE * CFG["spacing_ratio"])
NUM_SEGMENTS = CFG["num_segments"]
BASE_SPEED = float(CFG["base_speed"])
MAX_SPEED = float(CFG["max_speed"])
SLOW_DURATION = float(CFG["slow_duration"])
RAMP_DURATION = float(CFG["ramp_duration"])

DESTROY_DURATION = float(CFG.get("destroy_duration", 5.0))
DETERIORATE_DELAY = float(CFG.get("deteriorate_delay", 0.4))
DETERIORATE_DURATION = float(CFG.get("deteriorate_duration", 0.2))
FALL_DURATION = float(CFG.get("fall_duration", 2.0))
BREAK_APART = bool(CFG.get("break_apart", True))

DYING_SPEED = float(CFG.get("dying_speed", 10.0))
DYING_GRAVITY = float(CFG.get("dying_gravity", 20.0))
BREAK_POP_FORCE = float(CFG.get("break_pop_force", 4.0))
WIGGLE = float(CFG["wiggle"])
TURN_SMOOTHING = float(CFG["turn_smoothing"])
MAX_BEND_RAD = math.radians(float(CFG.get("max_bend_deg", 35.0)))
SPAWN_FROM_EDGE = CFG.get("spawn_from_edge", "random")
SPAWN_MARGIN = float(CFG.get("spawn_margin", 128))
WANDER_ARRIVE_DIST = float(CFG.get("wander_arrive_dist", 40.0))
ROTATE_HEAD = bool(CFG["rotate_head"])
ROTATE_BODY = bool(CFG["rotate_body"])
IMAGES_FACE_RIGHT = bool(CFG["images_face_right"])
HARD_EDGES = bool(CFG["hard_edges"])
FPS_MS = int(CFG["fps_ms"])
IDLE_FPS_MS = float(CFG.get("idle_fps_ms", FPS_MS))
IDLE_THRESHOLD = float(CFG.get("idle_threshold", 1.0))
DT = FPS_MS / 1000.0

IMAGE_DIR = CFG["image_dir"]
HEAD_FILE = CFG["head_file"]
BODY_FILE = CFG["body_file"]
TAIL_FILE = CFG["tail_file"]

# AI Movement Constants
WANDER_SPEED = 6.0
WANDER_MIN_PAUSE = 0.0
WANDER_MAX_PAUSE = 0.0
DECEL_DIST = 180.0
ACCEL_DIST = 120.0
EVADE_THREAT_DIST = 450.0

TWO_PI = math.pi * 2
RAD_TO_DEG = 180.0 / math.pi
PI_HALF = math.pi / 2.0

# Dialogue / Speech Constants
DIALOGUE_FILE = CFG.get("dialogue_file", "dog_lines.txt")
SPEECH_INTERVAL_MIN = float(CFG.get("speech_interval_min", 3.0))
SPEECH_INTERVAL_MAX = float(CFG.get("speech_interval_max", 8.0))
SPEECH_DURATION = float(CFG.get("speech_duration", 4.0))
SPEECH_FADE_DURATION = float(CFG.get("speech_fade_duration", 1.0))
SPEECH_FONT_FAMILY = CFG.get("speech_font_family", "Arial")
SPEECH_FONT_SIZE = int(CFG.get("speech_font_size", 16))
SPEECH_FONT_WEIGHT = CFG.get("speech_font_weight", "bold")
SPEECH_COLOR = CFG.get("speech_color", "#FFFFFF")
SPEECH_OFFSET_Y = float(CFG.get("speech_offset_y", 30))
SPEECH_SHAKE_AMOUNT = float(CFG.get("speech_shake_amount", 3.0))
SPEECH_BASE_COLOR = CFG.get("speech_color", "#947CE9")  # Purple hex
SPEECH_OPACITY = 1.0  # 0.0 (fully invisible) to 1.0 (fully opaque)