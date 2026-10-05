"""Speech text above the worm's head."""
import os
import random
import time

import tuning as T
from chain import segments
from params import P
from state import S


def _hex_to_rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def blend_hex_color(fg, bg, alpha):
    f, b = _hex_to_rgb(fg), _hex_to_rgb(bg)
    return "#" + "".join(f"{int(f[i] * alpha + b[i] * (1 - alpha)):02x}" for i in range(3))


class Speech:
    def __init__(self, canvas):
        self.canvas = canvas
        self.paths = {
            "normal": os.path.join(P.BASE_DIR, P.DIALOGUE_FILE),
            "chase": os.path.join(P.BASE_DIR, P.DIALOGUE_FILE_CHASE),
            "phase2": os.path.join(P.BASE_DIR, P.DIALOGUE_FILE_PHASE2),
        }
        self.pools = {}
        self.load()
        self.text_id = canvas.create_text(-1000, -1000, text="", font=self._font(),
                                          fill=P.SPEECH_COLOR, anchor="center")
        self.line = ""
        self.start = 0.0
        self.x = self.y = 0.0
        self.state = "normal"
        self.next_time = time.time() + random.uniform(P.SPEECH_INTERVAL_MIN, P.SPEECH_INTERVAL_MAX)

    def _font(self):
        return (P.SPEECH_FONT_FAMILY, P.SPEECH_FONT_SIZE, P.SPEECH_FONT_WEIGHT)

    def refresh_font(self):
        self.canvas.itemconfig(self.text_id, font=self._font())

    def load(self):
        for state, path in self.paths.items():
            lines = []
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        lines = [ln.strip() for ln in f if ln.strip()]
                except Exception as e:
                    print(f"Error reading {os.path.basename(path)}: {e}")
            self.pools[state] = lines

    def _pool(self, state):
        return self.pools.get(state) or self.pools["normal"]  # empty file -> normal lines

    def _current_state(self):
        if S.phase == 2:
            return "phase2"
        return "chase" if S.mode == "chase" else "normal"

    def _hide(self):
        self.canvas.itemconfig(self.text_id, state="hidden")

    def _say(self, state):
        pool = self._pool(state)
        if not pool:
            self.load()
            pool = self._pool(state)
        if not pool:
            return
        head = segments[0]
        self.line = random.choice(pool)
        self.start = time.time()
        self.x, self.y = head[0], head[1] + P.SPEECH_OFFSET_Y
        self.canvas.itemconfig(self.text_id, text=self.line, state="normal")

    def update(self, suppressed):
        if suppressed:
            self._hide()
            return
        now = time.time()

        state = self._current_state()
        if state != self.state:  # drop the old line, speak from the new pool soon
            self.state = state
            self.line = ""
            self._hide()
            self.next_time = now + T.SPEECH_STATE_SWITCH_DELAY

        if not self.line and now >= self.next_time:
            self._say(state)
            self.next_time = now + P.SPEECH_DURATION + random.uniform(P.SPEECH_INTERVAL_MIN, P.SPEECH_INTERVAL_MAX)

        if not self.line:
            return
        elapsed = now - self.start
        if elapsed >= P.SPEECH_DURATION:
            self.line = ""
            self._hide()
            return

        s = P.SPEECH_SHAKE_AMOUNT
        sx = random.uniform(-s, s) if s > 0 else 0
        sy = random.uniform(-s, s) if s > 0 else 0

        alpha = P.SPEECH_OPACITY
        fade_start = P.SPEECH_DURATION - P.SPEECH_FADE_DURATION
        if P.SPEECH_FADE_DURATION > 0 and elapsed > fade_start:
            alpha = max(0.0, alpha * (1.0 - (elapsed - fade_start) / P.SPEECH_FADE_DURATION))

        self.canvas.itemconfig(self.text_id, fill=blend_hex_color(P.SPEECH_BASE_COLOR, T.KEY, alpha))
        self.canvas.coords(self.text_id, self.x + sx, self.y + sy)
