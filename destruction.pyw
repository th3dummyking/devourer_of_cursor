"""
destruction.py - Low-CPU tail-to-head destruction animation logic and image caching.
"""
import random
import time
from PIL import Image, ImageChops, ImageTk

RESAMPLING = getattr(Image, "Resampling", Image)
BICUBIC = RESAMPLING.BICUBIC
NEAREST = RESAMPLING.NEAREST

# Deterioration look
ASH_COLOR = (40, 32, 28)   # color segments rot toward
ASH_MAX_BLEND = 0.35       # was 0.85, less darkening
SHRINK_END = 0.2           # shrinks closer to the old behavior
DISSOLVE_AMOUNT = 0.4      # 0 = no dissolve, 1 = full    # 0..1, how ashy they get at the end
SHRINK_END = 0.55          # final size as a fraction of the original (1.0 = no shrink)
CACHE_LIMIT = 600          # prevents unbounded growth from rotating images


class DestructionAnimator:
    def __init__(self, segment_size, num_segments, destroy_duration, deteriorate_delay=0.6, deteriorate_duration=0.8):
        self.segment_size = segment_size
        self.num_segments = num_segments
        self.destroy_duration = float(destroy_duration)
        self.deteriorate_delay = float(deteriorate_delay)
        self.deteriorate_duration = float(deteriorate_duration)
        
        self._noise = {}
        self.is_destroying = False
        self.start_time = 0.0
        self._cache = {}
        self.detach_times = {}

    def start(self):
        """Triggers the destruction animation sequence once."""
        if not self.is_destroying:
            self.is_destroying = True
            self.start_time = time.time()
            self.detach_times.clear()

    def reset(self):
        """Cancels destruction and resets back to normal state."""
        self._noise.clear()
        self.is_destroying = False
        self.start_time = 0.0
        self._cache.clear()
        self.detach_times.clear()

    @property
    def elapsed(self):
        if not self.is_destroying:
            return 0.0
        return max(0.0, time.time() - self.start_time)

    @property
    def progress(self):
        if not self.is_destroying or self.destroy_duration <= 0:
            return 0.0
        return min(1.0, self.elapsed / self.destroy_duration)

    @property
    def is_finished(self):
        """Returns True when all segments have finished their deterioration lifecycle."""
        if not self.is_destroying:
            return False
        total_needed_time = self.destroy_duration + self.deteriorate_delay + self.deteriorate_duration
        return self.elapsed >= total_needed_time

    def is_segment_started(self, segment_index):
        """Returns True if the destruction wave has reached the given segment."""
        if not self.is_destroying:
            return False
        tail_first_index = (self.num_segments - 1) - segment_index
        seg_start = tail_first_index / float(self.num_segments)
        return self.progress >= seg_start

    def mark_detached(self, segment_index):
        """Records the exact timestamp when a segment popped off."""
        if segment_index not in self.detach_times:
            self.detach_times[segment_index] = time.time()

    def _get_noise(self, idx, w, h):
        """Stable per-segment noise so the dissolve doesn't flicker between frames."""
        s = max(1, int(self.segment_size))
        key = (idx, s)
        noise = self._noise.get(key)
        if noise is None:
            rng = random.Random(idx * 7919 + 13)
            noise = Image.frombytes("L", (s, s), bytes(rng.randrange(256) for _ in range(s * s)))
            self._noise[key] = noise
        return noise.resize((w, h), NEAREST)

    def get_segment_photo(self, segment_index, base_pil_img):
        if not self.is_destroying or segment_index not in self.detach_times:
            return ImageTk.PhotoImage(base_pil_img)

        since = time.time() - self.detach_times[segment_index]
        if since < self.deteriorate_delay:
            decay = 0.0
        elif self.deteriorate_duration <= 0:
            decay = 1.0
        else:
            decay = min(1.0, (since - self.deteriorate_delay) / self.deteriorate_duration)

        if decay >= 0.98:
            return None

        q = int(round(decay * 20))  # 0 = fresh, 20 = gone
        key = (id(base_pil_img), segment_index, q)

        if key not in self._cache:
            if len(self._cache) > CACHE_LIMIT:
                self._cache.clear()
            t = q / 20.0
            scale = 1.0 - (1.0 - SHRINK_END) * t
            w = h = max(1, int(self.segment_size * scale))

            img = base_pil_img.convert("RGBA").resize((w, h), BICUBIC)
            r, g, b, a = img.split()

            # 1) Rot toward ash color
            ash = min(1.0, t * 1.5) * ASH_MAX_BLEND
            if ash > 0:
                rgb = Image.blend(Image.merge("RGB", (r, g, b)), Image.new("RGB", (w, h), ASH_COLOR), ash)
                r, g, b = rgb.split()

            # 2) Dissolve: random pixels drop out as decay grows
            if t > 0:
                threshold = int(255 * t * DISSOLVE_AMOUNT)
                keep = self._get_noise(segment_index, w, h).point(lambda v: 255 if v >= threshold else 0)
                a = ImageChops.multiply(a, keep)
                # 3) Gentle overall fade in the last stretch
                fade = 1.0 - t ** 3
                a = a.point(lambda v: int(v * fade))

            self._cache[key] = ImageTk.PhotoImage(Image.merge("RGBA", (r, g, b, a)))

        return self._cache[key]