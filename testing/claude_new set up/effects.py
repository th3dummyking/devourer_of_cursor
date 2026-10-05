"""Pixel-style explosion particles."""
import math
import random
import time

import tuning as T
from params import P


def _stipple_for(alpha):
    for threshold, name in T.STIPPLE_LEVELS:
        if alpha >= threshold:
            return name
    return T.STIPPLE_LEVELS[-1][1]


class Particles:
    def __init__(self, canvas):
        self.canvas = canvas
        self.items = []

    def _px(self):
        return max(2, round(T.EXPLOSION_PIXEL * P.SCALE))

    def _add(self, x, y, vx, vy, size, life, color, gravity):
        px = self._px()
        cells = max(1, round(size / px))
        stip = _stipple_for(T.EXPLOSION_OPACITY)
        gx, gy = round(x / px) * px, round(y / px) * px
        item = self.canvas.create_rectangle(gx, gy, gx + cells * px, gy + cells * px,
                                            fill=color, outline="", stipple=stip)
        self.items.append({"id": item, "x": x, "y": y, "vx": vx, "vy": vy, "cells": cells,
                           "born": time.time(), "life": life, "g": gravity, "stip": stip})

    def explode(self, x, y):
        self._add(x, y, 0, 0, T.EXPLOSION_FLASH_SIZE * P.SCALE, 0.15, "#ffffff", 0.0)  # flash
        for _ in range(T.EXPLOSION_PARTICLES):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(*T.EXPLOSION_SPEED) * P.SCALE
            self._add(x, y, math.cos(ang) * spd, math.sin(ang) * spd,
                      random.uniform(*T.EXPLOSION_SIZE) * P.SCALE,
                      random.uniform(*T.EXPLOSION_LIFE),
                      random.choice(T.EXPLOSION_COLORS),
                      T.EXPLOSION_GRAVITY * P.SCALE)

    def update(self):
        now = time.time()
        px = self._px()
        alive = []
        for p in self.items:
            t = (now - p["born"]) / p["life"]
            if t >= 1.0:
                self.canvas.delete(p["id"])
                continue
            p["vy"] += p["g"]
            p["vx"] *= 0.95
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            c = max(1, round(p["cells"] * (1.0 - t)))
            gx, gy = round(p["x"] / px) * px, round(p["y"] / px) * px
            self.canvas.coords(p["id"], gx, gy, gx + c * px, gy + c * px)
            stip = _stipple_for(T.EXPLOSION_OPACITY * (1.0 - t))
            if stip != p["stip"]:
                self.canvas.itemconfig(p["id"], stipple=stip)
                p["stip"] = stip
            alive.append(p)
        self.items = alive
