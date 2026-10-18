"""Phase 1 <-> 2 switch: dash off-screen, resize, respawn."""
import math
import time

import win_utils
import tuning as T
from chain import segment_angles, segments, spawn_worm
from params import P, apply_scale
from state import S


def start_phase_change():
    """Pick an exit edge (nearest, biased toward the head's heading) and start the dash."""
    S.dash_target_phase = 2 if S.phase == 1 else 1
    head, heading = segments[0], segment_angles[0]
    half = math.pi / 2
    best = None
    for edge_angle, edge_dist in (
        (math.pi, head[0]),
        (0.0, win_utils.VW - head[0]),
        (-half, head[1]),
        (half, win_utils.VH - head[1]),
    ):
        turn = abs((edge_angle - heading + math.pi) % math.tau - math.pi)
        score = max(0.0, edge_dist) + T.PHASE_DASH_TURN_PENALTY * turn
        if best is None or score < best[0]:
            best = (score, edge_angle)
    S.dash_angle = best[1]
    S.dash_start_time = time.time()
    S.dash_active = True


def dash_finished(now):
    if now - S.dash_start_time > T.PHASE_DASH_TIMEOUT:
        return True
    m = P.SEGMENT_SIZE
    return not any(-m <= x <= win_utils.VW + m and -m <= y <= win_utils.VH + m for x, y in segments)


def finish_phase_change(animator, speech):
    S.dash_active = False
    S.phase = S.dash_target_phase
    apply_scale(P.PHASE2_SCALE if S.phase == 2 else 1.0)
    animator.segment_size = P.SEGMENT_SIZE  # keep the death animation sized correctly
    speech.refresh_font()
    spawn_worm()
    S.reset_motion()
