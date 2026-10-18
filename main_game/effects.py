"""High-resolution anti-aliased particle effects."""
import math
import random
import time

import tuning as T
from params import P


class Particles:
    def __init__(self, canvas):
        self.canvas = canvas
        self.items = []

    def _px(self):
        # Change this factor to adjust pixel grain size:
        # 1 = sharp 1px fine pixels
        # 2 = subtle retro 2px pixels (recommended)
        # 3+ = blockier retro pixels
        return max(1, round(1.5 * P.SCALE))

    def _add(self, x, y, vx, vy, radius, life, color, gravity):
        # Draw smooth circles instead of blocky stippled rectangles
        item = self.canvas.create_oval(
            x - radius, y - radius, x + radius, y + radius,
            fill=color, outline=""
        )
        self.items.append({
            "id": item, "x": x, "y": y, "vx": vx, "vy": vy,
            "base_radius": radius, "born": time.time(), "life": life, "g": gravity
        })

    def explode(self, x, y):
        # No particle may outlive the animation's end window
        life_cap = P.DETERIORATE_DELAY + P.DETERIORATE_DURATION + 0.2

        # Center flash burst
        self._add(x, y, 0, 0, T.EXPLOSION_FLASH_SIZE * P.SCALE * 0.8,
                min(0.12, life_cap), "#ffffff", 0.0)

        for _ in range(T.EXPLOSION_PARTICLES):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(*T.EXPLOSION_SPEED) * P.SCALE
            radius = random.uniform(2.0, 4.5) * P.SCALE
            self._add(
                x, y,
                math.cos(ang) * spd, math.sin(ang) * spd,
                radius,
                min(random.uniform(*T.EXPLOSION_LIFE), life_cap),
                random.choice(T.EXPLOSION_COLORS),
                T.EXPLOSION_GRAVITY * P.SCALE
            )

    # effects.py, inside class Particles
    @property
    def empty(self):
        return not self.items

    def update(self):
        now = time.time()
        alive = []
        for p in self.items:
            t = (now - p["born"]) / p["life"]
            if t >= 1.0:
                self.canvas.delete(p["id"])
                continue

            # Physics updates with smooth air resistance
            p["vy"] += p["g"]
            p["vx"] *= 0.94
            p["vy"] *= 0.98
            p["x"] += p["vx"]
            p["y"] += p["vy"]

            # Smoothly shrink radius over lifetime
            r = p["base_radius"] * (1.0 - (t ** 0.8))
            if r < 0.5:
                self.canvas.delete(p["id"])
                continue

            self.canvas.coords(p["id"], p["x"] - r, p["y"] - r, p["x"] + r, p["y"] + r)
            alive.append(p)
        self.items = alive