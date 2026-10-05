"""
destruction.py - Low-CPU tail-to-head destruction animation logic and image caching.
"""
import time
from PIL import Image, ImageTk

RESAMPLING = getattr(Image, "Resampling", Image)
BICUBIC = RESAMPLING.BICUBIC


class DestructionAnimator:
    def __init__(self, segment_size, num_segments, destroy_duration, deteriorate_delay=0.6, deteriorate_duration=0.8):
        self.segment_size = segment_size
        self.num_segments = num_segments
        self.destroy_duration = float(destroy_duration)
        self.deteriorate_delay = float(deteriorate_delay)
        self.deteriorate_duration = float(deteriorate_duration)
        
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

    def get_segment_photo(self, segment_index, base_pil_img):
        """
        Fast cached scaled/faded PhotoImage generation.
        """
        if not self.is_destroying or segment_index not in self.detach_times:
            return ImageTk.PhotoImage(base_pil_img)

        time_since_detach = time.time() - self.detach_times[segment_index]

        if time_since_detach < self.deteriorate_delay:
            seg_factor = 1.0
        else:
            decay_elapsed = time_since_detach - self.deteriorate_delay
            if self.deteriorate_duration <= 0:
                seg_factor = 0.0
            else:
                seg_factor = max(0.0, 1.0 - (decay_elapsed / self.deteriorate_duration))

        if seg_factor <= 0.02:
            return None

        # Quantize scale and alpha to steps of 0.05 to minimize cache bloat and resize CPU load
        q_scale_int = int(round(seg_factor * 20))
        q_alpha_int = q_scale_int
        
        key = (id(base_pil_img), q_scale_int, q_alpha_int)

        if key not in self._cache:
            factor = q_scale_int / 20.0
            w = max(1, int(self.segment_size * factor))
            h = max(1, int(self.segment_size * factor))
            
            resized = base_pil_img.resize((w, h), BICUBIC)

            # Fast transparency scaling
            if factor < 0.99:
                r, g, b, a = resized.split()
                alpha_mult = factor
                a = Image.eval(a, lambda v: int(v * alpha_mult))
                resized.putalpha(a)

            self._cache[key] = ImageTk.PhotoImage(resized)

        return self._cache[key]