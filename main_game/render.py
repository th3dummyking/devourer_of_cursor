"""Draws the worm segments on the canvas."""
import math

import tuning as T
from assets import get_base_photo, get_base_tk_photo
from chain import NUM_SEGMENTS, broken_physics, draw_angles, segment_angles, segments
from params import P
from state import S

TAIL_OVERLAP = 2  # how many of the last body segments the tail covers

class WormRenderer:
    def __init__(self, canvas, animator):
        self.canvas = canvas
        self.animator = animator
        self.items = [canvas.create_image(-100, -100) for _ in range(NUM_SEGMENTS)]
        
        for item in reversed(self.items[1:-1]):  # body
            canvas.tag_raise(item)
        # tail goes just above the last TAIL_OVERLAP body segments, below the rest
        ref = self.items[max(1, NUM_SEGMENTS - 1 - TAIL_OVERLAP)]
        canvas.tag_raise(self.items[-1], ref)
        canvas.tag_raise(self.items[0])   # head on top of everything
        self.photos = [None] * NUM_SEGMENTS  # keep references so Tk doesn't GC the images

    def draw(self):
        animator = self.animator
        wiggle_base = S.tick * 0.2
        wiggle_decay = (1.0 - animator.progress) if animator.is_destroying else 1.0
        body_smoothing = T.BODY_FOLLOW_STIFFNESS if S.mode == "box" else P.TURN_SMOOTHING

        for i in range(NUM_SEGMENTS):
            x, y = segments[i]

            if not broken_physics[i]["detached"]:
                if i == 0:
                    fx, fy = x - segments[1][0], y - segments[1][1]
                else:
                    fx, fy = segments[i - 1][0] - x, segments[i - 1][1] - y
                target = math.atan2(fy, fx) if (fx or fy) else segment_angles[i]
                a = segment_angles[i]
                diff = (target - a + math.pi) % math.tau - math.pi
                heading = a + diff * (P.TURN_SMOOTHING if i == 0 else body_smoothing)
                segment_angles[i] = heading

                if i > 0 and P.WIGGLE:
                    w = math.sin(wiggle_base - i * 0.6) * P.WIGGLE * wiggle_decay
                    perp = heading + math.pi / 2
                    x += math.cos(perp) * w
                    y += math.sin(perp) * w

                angle = -heading * P.RAD_TO_DEG
                if not P.IMAGES_FACE_RIGHT:
                    angle -= 90.0
                draw_angles[i] = angle
            else:
                angle = broken_physics[i]["rot"]

            tag = "head" if i == 0 else ("tail" if i == NUM_SEGMENTS - 1 else "body")
            if S.phase == 2:
                tag += "2"

            if animator.is_destroying:
                photo = animator.get_segment_photo(i, get_base_photo(tag, angle), angle)
            else:
                photo = get_base_tk_photo(tag, angle)
            self.photos[i] = photo

            if photo is None:
                self.canvas.itemconfig(self.items[i], state="hidden")
            else:
                self.canvas.itemconfig(self.items[i], image=photo, state="normal")
                self.canvas.coords(self.items[i], x, y)
