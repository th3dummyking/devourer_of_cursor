"""All mutable runtime state in one place."""
import random

from params import P


class State:
    def __init__(self):
        self.tick = 0
        self.quit_flag = False
        self.mode = "evade"  # evade | wander | chase | box
        self.phase = 1
        self.idle_start = None
        self.death_curl_dir = random.choice((-1, 1))

        # wander / box
        self.wander_target = None
        self.wander_pause_until = 0.0
        self.wander_start_pos = None
        self.current_corner_idx = None
        self.circuit_idx = 0

        # phase-change dash
        self.dash_active = False
        self.dash_target_phase = 2
        self.dash_angle = 0.0
        self.dash_start_time = 0.0

        self.reset_motion()

    def reset_motion(self):
        self.chase_time = 0.0
        self.wander_target = None
        self.wander_pause_until = 0.0
        self.wander_start_pos = None
        self.last_evade_check = 0.0
        self.evade_speed_last_check = 0.0
        self.locked_evade_angle = 0.0
        self.locked_evade_speed = P.WANDER_SPEED
        self.current_evade_speed = P.WANDER_SPEED

    def toggle_mode(self, name):
        self.mode = "evade" if self.mode == name else name
        self.wander_target = None
        self.chase_time = 0.0


S = State()
