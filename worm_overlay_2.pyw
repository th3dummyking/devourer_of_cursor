import math
import os
import random
import sys
import time
import tkinter as tk

from assets import get_base_photo, get_base_tk_photo, head_img, init_assets
from config import (
    ACCEL_DIST,
    BASE_DIR,
    BASE_SPEED,
    BREAK_APART,
    BREAK_POP_FORCE,
    DECEL_DIST,
    DESTROY_DURATION,
    DETERIORATE_DELAY,
    DETERIORATE_DURATION,
    DIALOGUE_FILE,
    DIALOGUE_FILE_CHASE,
    DIALOGUE_FILE_PHASE2,
    DT,
    DYING_GRAVITY,
    DYING_SPEED,
    EVADE_THREAT_DIST,
    FPS_MS,
    IDLE_FPS_MS,
    IDLE_THRESHOLD,
    IMAGES_FACE_RIGHT,
    MAX_BEND_RAD,
    MAX_SPEED,
    NUM_SEGMENTS,
    PI_HALF,
    RAD_TO_DEG,
    RAMP_DURATION,
    SEGMENT_SIZE,
    SLOW_DURATION,
    SPACING,
    SPAWN_FROM_EDGE,
    SPAWN_MARGIN,
    SPEECH_COLOR,
    SPEECH_DURATION,
    SPEECH_FADE_DURATION,
    SPEECH_FONT_FAMILY,
    SPEECH_FONT_SIZE,
    SPEECH_FONT_WEIGHT,
    SPEECH_INTERVAL_MAX,
    SPEECH_INTERVAL_MIN,
    SPEECH_OFFSET_Y,
    SPEECH_SHAKE_AMOUNT,
    TURN_SMOOTHING,
    TWO_PI,
    WANDER_ARRIVE_DIST,
    WANDER_MAX_PAUSE,
    WANDER_MIN_PAUSE,
    WANDER_SPEED,
    WIGGLE,
    SPEECH_OPACITY,
    SPEECH_BASE_COLOR,
    PHASE2_DASH_SPEED_MULT,
    PHASE2_SCALE,
    scaled_params,
)
from destruction import DestructionAnimator
import win_utils

# Corner Box Configuration (Wander Mode)
CORNER_WIDTH_RATIO = 0.15   # Fraction of screen width used for corner targets
CORNER_HEIGHT_RATIO = 0.15  # Fraction of screen height used for corner targets

# Screen Circuit Mode Configuration (Top-Left -> Top-Right -> Bottom-Right -> Bottom-Left)
MARGIN = -10
CIRCUIT_WAYPOINTS = [
    (MARGIN, MARGIN),                      # Top-Left
    (win_utils.VW - MARGIN, MARGIN),       # Top-Right
    (win_utils.VW - MARGIN, win_utils.VH - MARGIN), # Bottom-Right
    (MARGIN, win_utils.VH - MARGIN)        # Bottom-Left
]
CIRCUIT_ARRIVE_DIST = 80.0  # Distance before starting bezier curve turn

# Phase Change (Ctrl+Alt+P) Configuration
PHASE_DASH_TIMEOUT = 4.0          # Failsafe: force the respawn if the dash takes longer than this (seconds)
PHASE_DASH_TURN_PENALTY = 400.0   # Higher = prefers the exit edge the worm already faces, lower = nearest edge
SPEECH_STATE_SWITCH_DELAY = 0.5   # Seconds before the first line after the speech state changes

# Box Mode Speed & Movement Controls
CIRCUIT_SPEED_MULTIPLIER = 1.3   # Change this to speed up or slow down Box Mode (e.g. 1.2, 2.5)
BODY_FOLLOW_STIFFNESS = 1     # Body curvature ratio (0.20 = soft/flattened, 1.0 = sharp follow)
# Circuit Wave / Zigzag Configuration
WAVE_ENABLED = True           # Toggle wave motion on/off
WAVE_FREQUENCY = 4.5          # Speed/frequency of oscillations (higher = faster wiggles)
WAVE_AMPLITUDE = 0.7         # Offset angle in radians (~20 deg max deviation)
CIRCUIT_STEER_RATE = 0.30     # Steering responsiveness while tracking the wave

# Death Animation
DEATH_CRAWL_SPEED = 3.0      # initial head speed while dying
DEATH_CRAWL_DECAY = 2.0      # higher = stops crawling sooner
DEATH_WRITHE_AMOUNT = 0.25   # head wobble in radians
DEATH_WRITHE_FREQ = 16.0
EXPLOSION_PARTICLES = 13      # per segment
EXPLOSION_SPEED = (2.0, 6.5)
EXPLOSION_SIZE = (5.0, 10.0)
# EXPLOSION_SIZE = (2.0, 5.0)
EXPLOSION_LIFE = (0.35, 0.6)
EXPLOSION_GRAVITY = 0.18
EXPLOSION_FLASH_SIZE = 10.0  # brief bright puff at the pop point
EXPLOSION_COLORS = ["#2965f2", "#6e0591", "#BF52EA", "#cc9bfa"]
EXPLOSION_OPACITY = 0.4      # 0.0-1.0, starting opacity (fades out over each particle's life)
EXPLOSION_PIXEL = 4          # grid size in px; bigger = chunkier pixels
# (min opacity, stipple pattern), checked top to bottom
STIPPLE_LEVELS = [(0.88, ""), (0.62, "gray75"), (0.37, "gray50"), (0.18, "gray25"), (0.0, "gray12")]
# Window Setup
KEY = "#010101"
root = tk.Tk()
root.title("Worm")
root.overrideredirect(True)
root.attributes("-topmost", True)
root.attributes("-transparentcolor", KEY)
root.geometry(f"{win_utils.VW}x{win_utils.VH}{win_utils.VX:+d}{win_utils.VY:+d}")
root.config(bg=KEY)

# Precalculate ImageTk.PhotoImage objects AFTER root is created
init_assets()

canvas = tk.Canvas(root, bg=KEY, highlightthickness=0, bd=0)
canvas.pack(fill="both", expand=True)
root.update()

# Setup Animator
animator = DestructionAnimator(
    SEGMENT_SIZE,
    NUM_SEGMENTS,
    DESTROY_DURATION,
    deteriorate_delay=DETERIORATE_DELAY,
    deteriorate_duration=DETERIORATE_DURATION,
)

HWND = win_utils.user32.GetParent(root.winfo_id()) or root.winfo_id()
win_utils.make_click_through(HWND)
win_utils.keep_on_top(HWND)

# Speech Bubble / Text State Setup
# Three speech states: "normal", "chase" (following the cursor), "phase2" (second phase)
DIALOGUE_PATHS = {
    "normal": os.path.join(BASE_DIR, DIALOGUE_FILE),
    "chase": os.path.join(BASE_DIR, DIALOGUE_FILE_CHASE),
    "phase2": os.path.join(BASE_DIR, DIALOGUE_FILE_PHASE2),
}
dialogue_pools = {"normal": [], "chase": [], "phase2": []}


def load_dialogue_lines():
    for state, path in DIALOGUE_PATHS.items():
        lines = []
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f if line.strip()]
            except Exception as e:
                print(f"Error reading {os.path.basename(path)}: {e}")
        dialogue_pools[state] = lines


def get_dialogue_pool(state):
    # An empty/missing file for a state falls back to the normal lines
    return dialogue_pools.get(state) or dialogue_pools["normal"]


def get_speech_state():
    if phase == 2:
        return "phase2"
    if chase_mode:
        return "chase"
    return "normal"


load_dialogue_lines()

speech_text_id = canvas.create_text(
    -1000,
    -1000,
    text="",
    font=(SPEECH_FONT_FAMILY, SPEECH_FONT_SIZE, SPEECH_FONT_WEIGHT),
    fill=SPEECH_COLOR,
    anchor="center",
)

current_speech_line = ""
speech_start_time = 0.0
next_speech_time = time.time() + random.uniform(SPEECH_INTERVAL_MIN, SPEECH_INTERVAL_MAX)
speech_spawn_x = 0.0
speech_spawn_y = 0.0
speech_state = "normal"


def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip("#")
    if len(hex_str) == 3:
        hex_str = "".join([c * 2 for c in hex_str])
    return tuple(int(hex_str[i : i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def blend_hex_color(foreground_hex, background_hex, alpha):
    fg = hex_to_rgb(foreground_hex)
    bg = hex_to_rgb(background_hex)
    blended = tuple(int(fg[i] * alpha + bg[i] * (1.0 - alpha)) for i in range(3))
    return rgb_to_hex(blended)


def trigger_speech(x, y, state):
    global current_speech_line, speech_start_time, speech_spawn_x, speech_spawn_y
    pool = get_dialogue_pool(state)
    if not pool:
        load_dialogue_lines()
        pool = get_dialogue_pool(state)
    if pool:
        current_speech_line = random.choice(pool)
        speech_start_time = time.time()
        speech_spawn_x = x
        speech_spawn_y = y + SPEECH_OFFSET_Y
        canvas.itemconfig(speech_text_id, text=current_speech_line, state="normal")


def update_speech():
    global next_speech_time, current_speech_line, speech_state
    now = time.time()

    if quit_flag or animator.is_destroying or dash_active:
        canvas.itemconfig(speech_text_id, state="hidden")
        return

    # State changed (normal <-> chase, or phase 2 began): drop the old line, speak from the new pool soon
    state = get_speech_state()
    if state != speech_state:
        speech_state = state
        current_speech_line = ""
        canvas.itemconfig(speech_text_id, state="hidden")
        next_speech_time = now + SPEECH_STATE_SWITCH_DELAY

    # Trigger new speech line if due
    if not current_speech_line and now >= next_speech_time:
        head_x, head_y = segments[0][0], segments[0][1]
        trigger_speech(head_x, head_y, state)
        next_speech_time = now + SPEECH_DURATION + random.uniform(SPEECH_INTERVAL_MIN, SPEECH_INTERVAL_MAX)

    if current_speech_line:
        elapsed = now - speech_start_time
        if elapsed >= SPEECH_DURATION:
            current_speech_line = ""
            canvas.itemconfig(speech_text_id, state="hidden")
        else:
            shake_x = random.uniform(-SPEECH_SHAKE_AMOUNT, SPEECH_SHAKE_AMOUNT) if SPEECH_SHAKE_AMOUNT > 0 else 0
            shake_y = random.uniform(-SPEECH_SHAKE_AMOUNT, SPEECH_SHAKE_AMOUNT) if SPEECH_SHAKE_AMOUNT > 0 else 0
            
            draw_x = speech_spawn_x + shake_x
            draw_y = speech_spawn_y + shake_y

            fade_start = SPEECH_DURATION - SPEECH_FADE_DURATION

            if elapsed > fade_start and SPEECH_FADE_DURATION > 0:
                fade_progress = (elapsed - fade_start) / SPEECH_FADE_DURATION
                current_alpha = max(0.0, SPEECH_OPACITY * (1.0 - fade_progress))
                color = blend_hex_color(SPEECH_BASE_COLOR, KEY, current_alpha)
            else:
                color = blend_hex_color(SPEECH_BASE_COLOR, KEY, SPEECH_OPACITY)

            canvas.itemconfig(speech_text_id, fill=color)
            canvas.coords(speech_text_id, draw_x, draw_y)


# Spawn Calculation
def compute_spawn_point():
    edge = SPAWN_FROM_EDGE
    if edge == "random":
        edge = random.choice(["left", "right", "top", "bottom"])

    if edge == "left":
        return -SPAWN_MARGIN, random.uniform(0, win_utils.VH)
    elif edge == "right":
        return win_utils.VW + SPAWN_MARGIN, random.uniform(0, win_utils.VH)
    elif edge == "top":
        return random.uniform(0, win_utils.VW), -SPAWN_MARGIN
    else:
        return random.uniform(0, win_utils.VW), win_utils.VH + SPAWN_MARGIN


segments = []
segment_angles = []


def spawn_worm():
    """(Re)builds the whole chain just off-screen, heading toward the cursor. Uses the current phase's size."""
    cursor_x, cursor_y = win_utils.cursor_pos()
    sx, sy = compute_spawn_point()

    ddx, ddy = cursor_x - sx, cursor_y - sy
    ddist = math.hypot(ddx, ddy) or 1.0
    ux, uy = ddx / ddist, ddy / ddist

    segments[:] = [[sx - ux * i * SPACING, sy - uy * i * SPACING] for i in range(NUM_SEGMENTS)]
    segment_angles[:] = [math.atan2(uy, ux)] * NUM_SEGMENTS


spawn_worm()
items = [canvas.create_image(-100, -100) for _ in range(NUM_SEGMENTS)]

broken_physics = [
    {
        "detached": False,
        "detach_time": 0.0,
        "vx": 0.0,
        "vy": 0.0,
        "rot": 0.0,
        "rot_speed": 0.0,
    }
    for _ in range(NUM_SEGMENTS)
]

for i in range(NUM_SEGMENTS - 1, -1, -1):
    canvas.tag_raise(items[i])
canvas.tag_raise(speech_text_id)

# States
tick = 0
chase_time = 0.0
quit_flag = False
tray_icon = None
idle_start = None

wander_target = None
wander_pause_until = 0.0
wander_start_pos = None
current_corner_idx = None

circuit_idx = 0  # Index for Screen Circuit Mode

phase = 1            # 1 = first phase, 2 = second phase
SCALE = 1.0          # Size multiplier of the current phase (set by apply_phase)
dash_active = False  # True while the worm dashes off-screen before respawning in the other phase
dash_target_phase = 2
dash_angle = 0.0
dash_start_time = 0.0

wander_mode = False
chase_mode = False
box_mode = False
evade_mode = True

last_evade_check = 0.0
locked_evade_angle = 0.0
evade_speed_last_check = 0.0
locked_evade_speed = WANDER_SPEED
current_evade_speed = WANDER_SPEED

_wm_was_down = False
_cm_was_down = False
_rm_was_down = False
_phase_was_down = False


def request_quit():
    global quit_flag
    if not quit_flag:
        quit_flag = True
        animator.start()
        if tray_icon:
            tray_icon.stop()


def apply_phase(new_phase):
    """Swap every size-dependent value to the given phase's scale."""
    global phase
    phase = new_phase
    scale = PHASE2_SCALE if new_phase == 2 else 1.0
    # Overwrites SEGMENT_SIZE, SPACING, speeds, distances, wiggle, speech sizes, SCALE...
    globals().update(scaled_params(scale))
    animator.segment_size = SEGMENT_SIZE  # keeps the death animation sized correctly
    canvas.itemconfig(speech_text_id, font=(SPEECH_FONT_FAMILY, SPEECH_FONT_SIZE, SPEECH_FONT_WEIGHT))


def reset_motion_state():
    global chase_time, wander_target, wander_pause_until, wander_start_pos
    global last_evade_check, evade_speed_last_check, locked_evade_speed, current_evade_speed
    chase_time = 0.0
    wander_target = None
    wander_pause_until = 0.0
    wander_start_pos = None
    last_evade_check = 0.0
    evade_speed_last_check = 0.0
    locked_evade_speed = WANDER_SPEED
    current_evade_speed = WANDER_SPEED


def start_phase_change():
    """Pick an exit edge (nearest, biased toward the way the head already faces) and start the dash."""
    global dash_active, dash_angle, dash_start_time, dash_target_phase
    dash_target_phase = 2 if phase == 1 else 1  # Ctrl+Alt+P toggles between the two phases
    head = segments[0]
    heading = segment_angles[0]
    best = None
    for edge_angle, edge_dist in (
        (math.pi, head[0]),
        (0.0, win_utils.VW - head[0]),
        (-PI_HALF, head[1]),
        (PI_HALF, win_utils.VH - head[1]),
    ):
        turn = abs((edge_angle - heading + math.pi) % TWO_PI - math.pi)
        score = max(0.0, edge_dist) + PHASE_DASH_TURN_PENALTY * turn
        if best is None or score < best[0]:
            best = (score, edge_angle)
    dash_angle = best[1]
    dash_start_time = time.time()
    dash_active = True


def dash_cleared_screen():
    margin = SEGMENT_SIZE
    for x, y in segments:
        if -margin <= x <= win_utils.VW + margin and -margin <= y <= win_utils.VH + margin:
            return False
    return True


def finish_phase_change():
    """Worm is fully off-screen: despawn, swap to the target phase size/images, respawn from an edge."""
    global dash_active
    dash_active = False
    apply_phase(dash_target_phase)
    spawn_worm()
    reset_motion_state()


def wm_toggle_pressed():
    global _wm_was_down
    now_down = win_utils.is_key_down(0x57) and win_utils.is_key_down(0x4D)  # W + M
    edge = now_down and not _wm_was_down
    _wm_was_down = now_down
    return edge


def cm_toggle_pressed():
    global _cm_was_down
    now_down = win_utils.is_key_down(0x43) and win_utils.is_key_down(0x4D)  # C + M
    edge = now_down and not _cm_was_down
    _cm_was_down = now_down
    return edge


def rm_toggle_pressed():
    global _rm_was_down
    now_down = win_utils.is_key_down(0x52) and win_utils.is_key_down(0x4D)  # R + M
    edge = now_down and not _rm_was_down
    _rm_was_down = now_down
    return edge


def get_corner_target(head_x, head_y):
    global current_corner_idx

    margin = SPAWN_MARGIN
    corner_width = win_utils.VW * CORNER_WIDTH_RATIO
    corner_height = win_utils.VH * CORNER_HEIGHT_RATIO

    corners = [
        ((margin, corner_width), (margin, corner_height)),
        ((win_utils.VW - corner_width, win_utils.VW - margin), (margin, corner_height)),
        ((win_utils.VW - corner_width, win_utils.VW - margin), (win_utils.VH - corner_height, win_utils.VH - margin)),
        ((margin, corner_width), (win_utils.VH - corner_height, win_utils.VH - margin))
    ]

    if current_corner_idx is None:
        if head_x < win_utils.VW / 2:
            current_corner_idx = 0 if head_y < win_utils.VH / 2 else 3
        else:
            current_corner_idx = 1 if head_y < win_utils.VH / 2 else 2

    left_neighbor = (current_corner_idx - 1) % 4
    right_neighbor = (current_corner_idx + 1) % 4
    opposite = (current_corner_idx + 2) % 4
    same = current_corner_idx

    choices = [left_neighbor, right_neighbor, same, opposite]
    weights = [0.35, 0.35, 0.20, 0.10]

    chosen_corner_idx = random.choices(choices, weights=weights, k=1)[0]
    current_corner_idx = chosen_corner_idx

    (x_min, x_max), (y_min, y_max) = corners[chosen_corner_idx]
    tx = random.uniform(x_min, x_max)
    ty = random.uniform(y_min, y_max)

    return tx, ty


def relax_chain(max_bend_rad=None):
    prev_dir = None
    for i in range(1, NUM_SEGMENTS):
        prev, cur = segments[i - 1], segments[i]
        dx, dy = cur[0] - prev[0], cur[1] - prev[1]
        angle = math.atan2(dy, dx)

        if max_bend_rad is not None and prev_dir is not None:
            diff = (angle - prev_dir + math.pi) % TWO_PI - math.pi
            diff = max(-max_bend_rad, min(max_bend_rad, diff))
            angle = prev_dir + diff

        cur[0] = prev[0] + math.cos(angle) * SPACING
        cur[1] = prev[1] + math.sin(angle) * SPACING
        prev_dir = angle

particles = []
def _stipple_for(alpha):
    for threshold, name in STIPPLE_LEVELS:
        if alpha >= threshold:
            return name
    return "gray12"


def _add_particle(x, y, vx, vy, size, life, color, gravity):
    px = EXPLOSION_PIXEL
    cells = max(1, round(size / px))
    stip = _stipple_for(EXPLOSION_OPACITY)
    gx, gy = round(x / px) * px, round(y / px) * px
    item = canvas.create_rectangle(gx, gy, gx + cells * px, gy + cells * px,
                                   fill=color, outline="", stipple=stip)
    canvas.tag_lower(item)  # draw under the worm pieces so they stay visible
    particles.append({"id": item, "x": x, "y": y, "vx": vx, "vy": vy, "cells": cells,
                      "born": time.time(), "life": life, "g": gravity, "stip": stip})


def spawn_explosion(x, y):
    # Quick bright flash
    _add_particle(x, y, 0, 0, EXPLOSION_FLASH_SIZE * SCALE, 0.15, "#ffffff", 0.0)
    for _ in range(EXPLOSION_PARTICLES):
        ang = random.uniform(0, TWO_PI)
        spd = random.uniform(*EXPLOSION_SPEED) * SCALE
        _add_particle(
            x, y,
            math.cos(ang) * spd, math.sin(ang) * spd,
            random.uniform(*EXPLOSION_SIZE) * SCALE,
            random.uniform(*EXPLOSION_LIFE),
            random.choice(EXPLOSION_COLORS),
            EXPLOSION_GRAVITY * SCALE,
        )




def update_particles():
    now = time.time()
    px = EXPLOSION_PIXEL
    alive = []
    for p in particles:
        t = (now - p["born"]) / p["life"]
        if t >= 1.0:
            canvas.delete(p["id"])
            continue
        p["vy"] += p["g"]
        p["vx"] *= 0.95
        p["x"] += p["vx"]
        p["y"] += p["vy"]
        c = max(1, round(p["cells"] * (1.0 - t)))
        gx, gy = round(p["x"] / px) * px, round(p["y"] / px) * px
        canvas.coords(p["id"], gx, gy, gx + c * px, gy + c * px)
        stip = _stipple_for(EXPLOSION_OPACITY * (1.0 - t))
        if stip != p["stip"]:
            canvas.itemconfig(p["id"], stipple=stip)
            p["stip"] = stip
        alive.append(p)
    particles[:] = alive

def update_step():
    global tick, chase_time, idle_start, wander_mode, chase_mode, box_mode, evade_mode
    global wander_target, wander_pause_until, wander_start_pos, circuit_idx
    global last_evade_check, locked_evade_angle
    global evade_speed_last_check, locked_evade_speed, current_evade_speed
    global _phase_was_down

    tick += 1

    if win_utils.hotkey_pressed():
        request_quit()

    if not quit_flag:
        if wm_toggle_pressed():
            wander_mode = not wander_mode
            chase_mode = False
            box_mode = False
            evade_mode = not wander_mode
            wander_target = None

        if cm_toggle_pressed():
            chase_mode = not chase_mode
            wander_mode = False
            box_mode = False
            evade_mode = not chase_mode
            chase_time = 0.0

        if rm_toggle_pressed():
            box_mode = not box_mode
            wander_mode = False
            chase_mode = False
            evade_mode = not box_mode

        phase_down = win_utils.phase_hotkey_down()
        if phase_down and not _phase_was_down and not dash_active:
            start_phase_change()
        _phase_was_down = phase_down

        now = time.time()
        head = segments[0]
        target_angle = segment_angles[0]
        target_speed = 0.0
        steer_rate = TURN_SMOOTHING

        if dash_active:
            # Phase change: fly straight out through the chosen edge at full speed
            target_speed = MAX_SPEED * PHASE2_DASH_SPEED_MULT
            target_angle = dash_angle
            steer_rate = 0.25
            chase_time = 0.0
            idle_start = None

        elif box_mode:
            # Circuit path: Top-Left -> Top-Right -> Bottom-Right -> Bottom-Left -> Repeat
            tx, ty = CIRCUIT_WAYPOINTS[circuit_idx]
            dx, dy = tx - head[0], ty - head[1]
            dist = math.hypot(dx, dy)

            # Advance to the next corner waypoint when nearing the current target
            if dist < CIRCUIT_ARRIVE_DIST * SCALE:
                circuit_idx = (circuit_idx + 1) % len(CIRCUIT_WAYPOINTS)
                tx, ty = CIRCUIT_WAYPOINTS[circuit_idx]
                dx, dy = tx - head[0], ty - head[1]

            target_speed = BASE_SPEED * CIRCUIT_SPEED_MULTIPLIER
            base_angle = math.atan2(dy, dx)

            # Configurable wave motion calculation
            if WAVE_ENABLED:
                wave_offset = math.sin(now * WAVE_FREQUENCY) * WAVE_AMPLITUDE
                target_angle = base_angle + wave_offset
            else:
                target_angle = base_angle

            steer_rate = CIRCUIT_STEER_RATE
            idle_start = None

        elif wander_mode:
            if wander_target is None:
                wander_target = get_corner_target(head[0], head[1])
                wander_start_pos = (head[0], head[1])

            tx, ty = wander_target
            dx, dy = tx - head[0], ty - head[1]
            dist = math.hypot(dx, dy)

            if dist < WANDER_ARRIVE_DIST:
                if wander_pause_until == 0.0:
                    wander_pause_until = now + random.uniform(
                        WANDER_MIN_PAUSE, WANDER_MAX_PAUSE
                    )

                if now >= wander_pause_until:
                    wander_pause_until = 0.0
                    wander_target = None
                    wander_start_pos = None
                target_speed = 0.0
            else:
                wander_pause_until = 0.0
                if wander_start_pos is not None:
                    dist_from_start = math.hypot(
                        head[0] - wander_start_pos[0], head[1] - wander_start_pos[1]
                    )
                    accel_factor = min(1.0, dist_from_start / max(1.0, ACCEL_DIST))
                else:
                    accel_factor = 1.0

                decel_factor = min(1.0, dist / max(1.0, DECEL_DIST))
                smooth_factor = min(accel_factor, decel_factor)
                curve = smooth_factor * smooth_factor * (3 - 2 * smooth_factor)
                target_speed = max(1.0, WANDER_SPEED * curve)

                wander_drift = math.sin(now * 1.5) * 0.25
                target_angle = math.atan2(dy, dx) + wander_drift

            steer_rate = 0.10
            if target_speed > 0.0:
                idle_start = None
            elif idle_start is None:
                idle_start = time.time()

        elif chase_mode:
            tx, ty = win_utils.cursor_pos()
            dx, dy = tx - head[0], ty - head[1]
            dist = math.hypot(dx, dy)
            STOP_RADIUS = 25.0 * SCALE

            if dist > STOP_RADIUS:
                chase_time += DT
                if chase_time <= SLOW_DURATION:
                    target_speed = BASE_SPEED
                else:
                    ramp_t = min(1.0, (chase_time - SLOW_DURATION) / RAMP_DURATION)
                    curve = ramp_t**3.0
                    target_speed = BASE_SPEED + (MAX_SPEED - BASE_SPEED) * curve

                target_angle = math.atan2(dy, dx)
                proximity_factor = min(1.0, dist / (200.0 * SCALE))
                steer_rate = TURN_SMOOTHING + (1.0 - TURN_SMOOTHING) * (1.0 - proximity_factor)
                idle_start = None
            else:
                target_speed = 0.0
                chase_time = 0.0
                if idle_start is None:
                    idle_start = time.time()

        else:  # Evade Mode
            mx, my = win_utils.cursor_pos()
            dx, dy = head[0] - mx, head[1] - my
            dist = math.hypot(dx, dy)

            EVADE_PATH_COOLDOWN = 0.8
            EVADE_SPEED_COOLDOWN = 0.5
            EVADE_HOLD_DIST = 350.0 * SCALE
            IMMEDIATE_THREAT_DIST = 50.0 * SCALE

            if (now - last_evade_check) >= EVADE_PATH_COOLDOWN or dist < IMMEDIATE_THREAT_DIST:
                last_evade_check = now
                base_angle = math.atan2(dy, dx) if dist > 1e-5 else segment_angles[0]
                drift = math.sin(now * 1.4) * (math.pi / 4.0)
                locked_evade_angle = base_angle + drift

            if (now - evade_speed_last_check) >= EVADE_SPEED_COOLDOWN or dist < IMMEDIATE_THREAT_DIST:
                evade_speed_last_check = now
                if dist < EVADE_HOLD_DIST:
                    locked_evade_speed = MAX_SPEED * 0.90
                elif dist < EVADE_THREAT_DIST:
                    locked_evade_speed = MAX_SPEED * 0.50
                else:
                    locked_evade_speed = WANDER_SPEED * 1.1

            if locked_evade_speed > current_evade_speed:
                blend_rate = 0.25
            else:
                blend_rate = 0.03

            current_evade_speed += (locked_evade_speed - current_evade_speed) * blend_rate
            target_speed = current_evade_speed
            target_angle = locked_evade_angle

            proximity_factor = min(1.0, dist / IMMEDIATE_THREAT_DIST)
            steer_rate = 0.25 - (0.16 * proximity_factor)

            chase_time = 0.0
            idle_start = None

        # Boundary Steering
        steering_x, steering_y = 0.0, 0.0
        if not chase_mode and not box_mode and not dash_active:
            margin = SPAWN_MARGIN
            if head[0] < margin:
                steering_x += (margin - head[0]) / margin
            elif head[0] > win_utils.VW - margin:
                steering_x -= (head[0] - (win_utils.VW - margin)) / margin

            if head[1] < margin:
                steering_y += (margin - head[1]) / margin
            elif head[1] > win_utils.VH - margin:
                steering_y -= (head[1] - (win_utils.VH - margin)) / margin

        if (steering_x != 0.0 or steering_y != 0.0) and target_speed > 0.0:
            edge_avoid_angle = math.atan2(steering_y, steering_x)
            blend_weight = min(1.0, math.hypot(steering_x, steering_y))
            angle_diff = (edge_avoid_angle - target_angle + math.pi) % TWO_PI - math.pi
            target_angle += angle_diff * blend_weight

        # Steering step
        if target_speed > 0.0:
            curr_angle = segment_angles[0]
            angle_diff = (target_angle - curr_angle + math.pi) % TWO_PI - math.pi
            max_turn = math.pi if chase_mode else MAX_BEND_RAD * 0.75
            clamped_diff = max(-max_turn, min(max_turn, angle_diff * steer_rate))

            new_angle = curr_angle + clamped_diff
            segment_angles[0] = new_angle

            step_dist = target_speed * DT * 60.0
            if chase_mode:
                tx, ty = win_utils.cursor_pos()
                dist_to_cursor = math.hypot(tx - head[0], ty - head[1])
                step_dist = min(step_dist, max(1.0, dist_to_cursor - 25.0 * SCALE))

            head[0] += math.cos(new_angle) * step_dist
            head[1] += math.sin(new_angle) * step_dist

        relax_chain(MAX_BEND_RAD)

        if dash_active and (dash_cleared_screen() or now - dash_start_time > PHASE_DASH_TIMEOUT):
            finish_phase_change()

    elif BREAK_APART:
        # Dying crawl: the head keeps moving, slowing down and writhing, and the body gets dragged along
        if not broken_physics[0]["detached"]:
            t = animator.elapsed
            speed = DEATH_CRAWL_SPEED * SCALE * math.exp(-DEATH_CRAWL_DECAY * t)
            segment_angles[0] += math.sin(t * DEATH_WRITHE_FREQ) * DEATH_WRITHE_AMOUNT * math.exp(-1.5 * t)
            step = speed * DT * 60.0
            segments[0][0] += math.cos(segment_angles[0]) * step
            segments[0][1] += math.sin(segment_angles[0]) * step

        for i in range(NUM_SEGMENTS):
            p = broken_physics[i]
            if animator.is_segment_started(i):
                if not p["detached"]:
                    p["detached"] = True
                    ...  # existing code unchanged
                    animator.mark_detached(i)
                    spawn_explosion(segments[i][0], segments[i][1])   # <-- new line    else:
        for i in range(NUM_SEGMENTS):
            if animator.is_segment_started(i):
                animator.mark_detached(i)
        relax_chain(MAX_BEND_RAD)

    update_speech()
    update_particles()
    draw()




_active_photos = [None] * NUM_SEGMENTS


def draw():
    if WIGGLE != 0:
        wiggle_base = tick * 0.2
        wiggle_decay = (1.0 - animator.progress) if animator.is_destroying else 1.0

    # Increase turn responsiveness across the body when in Box Mode
    body_turn_smoothing = BODY_FOLLOW_STIFFNESS if box_mode else TURN_SMOOTHING

    for i in range(NUM_SEGMENTS):
        x, y = segments[i][0], segments[i][1]

        if not broken_physics[i]["detached"]:
            if i == 0:
                fx, fy = x - segments[1][0], y - segments[1][1]
            else:
                fx, fy = segments[i - 1][0] - x, segments[i - 1][1] - y

            target_heading = math.atan2(fy, fx) if (fx != 0.0 or fy != 0.0) else segment_angles[i]
            a = segment_angles[i]
            diff = (target_heading - a + math.pi) % TWO_PI - math.pi
            
            # Apply dynamic body turn smoothing
            smooth_rate = TURN_SMOOTHING if i == 0 else body_turn_smoothing
            heading = a + diff * smooth_rate
            segment_angles[i] = heading

            if i > 0 and WIGGLE != 0:
                w = math.sin(wiggle_base - i * 0.6) * WIGGLE * wiggle_decay
                perp = heading + PI_HALF
                x += math.cos(perp) * w
                y += math.sin(perp) * w

            angle = -heading * RAD_TO_DEG if IMAGES_FACE_RIGHT else -heading * RAD_TO_DEG - 90.0
        else:
            angle = broken_physics[i]["rot"]

        tag = "head" if i == 0 else ("tail" if i == NUM_SEGMENTS - 1 else "body")
        if phase == 2:
            tag += "2"

        if animator.is_destroying:
            base_pil = get_base_photo(tag, angle)
            photo = animator.get_segment_photo(i, base_pil)
        else:
            photo = get_base_tk_photo(tag, angle)

        _active_photos[i] = photo

        if photo is None:
            canvas.itemconfig(items[i], state="hidden")
        else:
            canvas.itemconfig(items[i], image=photo, state="normal")
            canvas.coords(items[i], x, y)

# Tray Icon Setup
try:
    import pystray

    tray_icon = pystray.Icon(
        "worm",
        head_img.resize((64, 64)),
        "Worm",
        menu=pystray.Menu(pystray.MenuItem("Quit", lambda icon, item: request_quit())),
    )
    tray_icon.run_detached()
except Exception:
    pass

# Main Loop
last_topmost = time.time()
running = True

while running and not animator.is_finished:
    start_loop = time.time()
    try:
        update_step()
        root.update()

        if start_loop - last_topmost > 2.0:
            win_utils.keep_on_top(HWND)
            last_topmost = start_loop

        if (not quit_flag) and idle_start is not None and (start_loop - idle_start) > IDLE_THRESHOLD:
            target_ms = IDLE_FPS_MS
        else:
            target_ms = FPS_MS

        elapsed = time.time() - start_loop
        sleep_time = max(0.001, (target_ms / 1000.0) - elapsed)
        time.sleep(sleep_time)
    except KeyboardInterrupt:
        request_quit()
    except tk.TclError:
        break

try:
    root.destroy()
except Exception:
    pass
sys.exit(0)