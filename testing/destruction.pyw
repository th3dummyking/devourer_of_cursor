"""
destruction.py - Low-CPU tail-to-head destruction animation logic and image caching.
"""
import random
import time
from PIL import Image, ImageChops, ImageTk

RESAMPLING = getattr(Image, "Resampling", Image)
BICUBIC = RESAMPLING.BICUBIC
BILINEAR = RESAMPLING.BILINEAR

ASH_COLOR = (40, 32, 28)
ASH_MAX_BLEND = 0.35
SHRINK_END = 0.55
DISSOLVE_AMOUNT = 0.5
CACHE_LIMIT = 1000

class DestructionAnimator:
    def __init__(self, segment_size, num_segments, destroy_duration, deteriorate_delay=0.3, deteriorate_duration=1.2):
        self.segment_size = segment_size
        self.num_segments = num_segments
        self.destroy_duration = float(destroy_duration + 5)
        self.deteriorate_delay = float(deteriorate_delay)
        self.deteriorate_duration = float(deteriorate_duration)
        self._live = {}
        
        self._noise = {}
        self.is_destroying = False
        self.start_time = 0.0
        self._cache = {}
        self.detach_times = {}

    def start(self):
        if not self.is_destroying:
            self.is_destroying = True
            self.start_time = time.time()
            self.detach_times.clear()

    def reset(self):
        self._noise.clear()
        self.is_destroying = False
        self.start_time = 0.0
        self._live.clear()
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

        # destruction.pyw
    @property
    def is_finished(self):
        if not self.is_destroying:
            return False
        # every segment must have detached
        if len(self.detach_times) < self.num_segments:
            return False
        last = max(self.detach_times.values())
        return time.time() - last >= (self.deteriorate_delay
                                    + self.deteriorate_duration + 0.2)
    def is_segment_started(self, segment_index):
        if not self.is_destroying:
            return False
        tail_first_index = (self.num_segments - 1) - segment_index
        seg_start = tail_first_index / float(self.num_segments)
        return self.progress >= seg_start

    def mark_detached(self, segment_index):
        if segment_index not in self.detach_times:
            self.detach_times[segment_index] = time.time()

    def _get_noise(self, idx, w, h):
        """Higher resolution smooth noise for high-fidelity dissolving."""
        s = max(64, int(self.segment_size * 2))  # Generate noise at higher resolution
        key = (idx, s)
        noise = self._noise.get(key)
        if noise is None:
            rng = random.Random(idx * 7919 + 13)
            noise = Image.frombytes("L", (s, s), bytes(rng.randrange(256) for _ in range(s * s)))
            self._noise[key] = noise
        return noise.resize((w, h), BILINEAR)  # Smooth out harsh noise grid

    def get_segment_photo(self, segment_index, base_pil_img, angle=0.0):
        if not self.is_destroying or segment_index not in self.detach_times:
            photo = ImageTk.PhotoImage(base_pil_img)
            self._live[segment_index] = photo
            return photo

        since = time.time() - self.detach_times[segment_index]
        if since < self.deteriorate_delay:
            decay = 0.0
        elif self.deteriorate_duration <= 0:
            decay = 1.0
        else:
            decay = min(1.0, (since - self.deteriorate_delay) / self.deteriorate_duration)

        if decay >= 0.98:
            
            return None

        # Increased resolution steps from 20 to 50 for smoother animation frames
        q = int(round(decay * 50))
        key = (segment_index, base_pil_img.size, int(angle) // 2, q)

        if key not in self._cache:
            if len(self._cache) > CACHE_LIMIT:
                self._cache.clear()
            t = q / 50.0
            scale = 1.0 - (1.0 - SHRINK_END) * t
            bw, bh = base_pil_img.size
            w = max(1, int(bw * scale))
            h = max(1, int(bh * scale))

            img = base_pil_img.convert("RGBA").resize((w, h), BICUBIC)
            r, g, b, a = img.split()

            # Smooth ash color transition
            ash = min(1.0, t * 1.2) * ASH_MAX_BLEND
            if ash > 0:
                rgb = Image.blend(Image.merge("RGB", (r, g, b)), Image.new("RGB", (w, h), ASH_COLOR), ash)
                r, g, b = rgb.split()

            # Smooth alpha dissolve
            if t > 0:
                threshold = int(255 * (t ** 1.5) * DISSOLVE_AMOUNT)
                keep = self._get_noise(segment_index, w, h).point(lambda v: 255 if v >= threshold else 0)
                a = ImageChops.multiply(a, keep)
                fade = max(0.0, 1.0 - (t ** 2))
                a = a.point(lambda v: int(v * fade))

            self._cache[key] = ImageTk.PhotoImage(Image.merge("RGBA", (r, g, b, a)))

        photo = self._cache[key]
        self._live[segment_index] = photo
        return photo