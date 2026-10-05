"""The worm's body: segment positions, spawning and bend-limited relaxation."""
import math
import random

import win_utils
from config import NUM_SEGMENTS
from params import P

segments = []          # [[x, y], ...]
segment_angles = []    # heading per segment (radians)
draw_angles = [0.0] * NUM_SEGMENTS  # last drawn image angle (degrees), used when a segment breaks off

broken_physics = [
    {"detached": False, "detach_time": 0.0, "vx": 0.0, "vy": 0.0, "rot": 0.0, "rot_speed": 0.0}
    for _ in range(NUM_SEGMENTS)
]


def compute_spawn_point():
    edge = P.SPAWN_FROM_EDGE
    if edge == "random":
        edge = random.choice(["left", "right", "top", "bottom"])
    m = P.SPAWN_MARGIN
    if edge == "left":
        return -m, random.uniform(0, win_utils.VH)
    if edge == "right":
        return win_utils.VW + m, random.uniform(0, win_utils.VH)
    if edge == "top":
        return random.uniform(0, win_utils.VW), -m
    return random.uniform(0, win_utils.VW), win_utils.VH + m


def spawn_worm():
    """(Re)build the chain just off-screen, heading toward the cursor, at the current phase's size."""
    cx, cy = win_utils.cursor_pos()
    sx, sy = compute_spawn_point()
    dx, dy = cx - sx, cy - sy
    dist = math.hypot(dx, dy) or 1.0
    ux, uy = dx / dist, dy / dist
    segments[:] = [[sx - ux * i * P.SPACING, sy - uy * i * P.SPACING] for i in range(NUM_SEGMENTS)]
    segment_angles[:] = [math.atan2(uy, ux)] * NUM_SEGMENTS


def relax(max_bend_rad=None, attached_only=False):
    """Follow-the-leader with an optional bend limit.
    attached_only stops at the first detached segment (used while dying)."""
    prev_dir = None
    for i in range(1, NUM_SEGMENTS):
        if attached_only and (broken_physics[i]["detached"] or broken_physics[i - 1]["detached"]):
            break
        prev, cur = segments[i - 1], segments[i]
        angle = math.atan2(cur[1] - prev[1], cur[0] - prev[0])
        if max_bend_rad is not None and prev_dir is not None:
            diff = (angle - prev_dir + math.pi) % math.tau - math.pi
            angle = prev_dir + max(-max_bend_rad, min(max_bend_rad, diff))
        cur[0] = prev[0] + math.cos(angle) * P.SPACING
        cur[1] = prev[1] + math.sin(angle) * P.SPACING
        prev_dir = angle
