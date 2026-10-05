"""Per-mode steering. Each _steer_* returns (target_angle, target_speed, steer_rate)."""
import math
import random

import win_utils
import tuning as T
from chain import segment_angles, segments
from params import P
from state import S


def _angle_diff(a, b):
    return (a - b + math.pi) % math.tau - math.pi


def _steer_dash(head, now):
    S.chase_time = 0.0
    return S.dash_angle, P.MAX_SPEED * P.PHASE2_DASH_SPEED_MULT, 0.25


def _steer_box(head, now):
    tx, ty = T.CIRCUIT_WAYPOINTS[S.circuit_idx]
    dx, dy = tx - head[0], ty - head[1]
    if math.hypot(dx, dy) < T.CIRCUIT_ARRIVE_DIST * P.SCALE:
        S.circuit_idx = (S.circuit_idx + 1) % len(T.CIRCUIT_WAYPOINTS)
        tx, ty = T.CIRCUIT_WAYPOINTS[S.circuit_idx]
        dx, dy = tx - head[0], ty - head[1]
    angle = math.atan2(dy, dx)
    if T.WAVE_ENABLED:
        angle += math.sin(now * T.WAVE_FREQUENCY) * T.WAVE_AMPLITUDE
    return angle, P.BASE_SPEED * T.CIRCUIT_SPEED_MULTIPLIER, T.CIRCUIT_STEER_RATE


def _corner_target(head):
    m = P.SPAWN_MARGIN
    vw, vh = win_utils.VW, win_utils.VH
    cw, ch = vw * T.CORNER_WIDTH_RATIO, vh * T.CORNER_HEIGHT_RATIO
    corners = [
        ((m, cw), (m, ch)),
        ((vw - cw, vw - m), (m, ch)),
        ((vw - cw, vw - m), (vh - ch, vh - m)),
        ((m, cw), (vh - ch, vh - m)),
    ]
    if S.current_corner_idx is None:
        if head[0] < vw / 2:
            S.current_corner_idx = 0 if head[1] < vh / 2 else 3
        else:
            S.current_corner_idx = 1 if head[1] < vh / 2 else 2
    cur = S.current_corner_idx
    choices = [(cur - 1) % 4, (cur + 1) % 4, cur, (cur + 2) % 4]
    S.current_corner_idx = random.choices(choices, weights=[0.35, 0.35, 0.20, 0.10], k=1)[0]
    (x0, x1), (y0, y1) = corners[S.current_corner_idx]
    return random.uniform(x0, x1), random.uniform(y0, y1)


def _steer_wander(head, now):
    if S.wander_target is None:
        S.wander_target = _corner_target(head)
        S.wander_start_pos = (head[0], head[1])
    tx, ty = S.wander_target
    dx, dy = tx - head[0], ty - head[1]
    dist = math.hypot(dx, dy)

    if dist < P.WANDER_ARRIVE_DIST:
        if S.wander_pause_until == 0.0:
            S.wander_pause_until = now + random.uniform(P.WANDER_MIN_PAUSE, P.WANDER_MAX_PAUSE)
        if now >= S.wander_pause_until:
            S.wander_pause_until = 0.0
            S.wander_target = None
            S.wander_start_pos = None
        return segment_angles[0], 0.0, 0.10

    S.wander_pause_until = 0.0
    accel = 1.0
    if S.wander_start_pos is not None:
        from_start = math.hypot(head[0] - S.wander_start_pos[0], head[1] - S.wander_start_pos[1])
        accel = min(1.0, from_start / max(1.0, P.ACCEL_DIST))
    decel = min(1.0, dist / max(1.0, P.DECEL_DIST))
    f = min(accel, decel)
    speed = max(1.0, P.WANDER_SPEED * f * f * (3 - 2 * f))
    angle = math.atan2(dy, dx) + math.sin(now * 1.5) * 0.25
    return angle, speed, 0.10


def _steer_chase(head, now):
    tx, ty = win_utils.cursor_pos()
    dx, dy = tx - head[0], ty - head[1]
    dist = math.hypot(dx, dy)
    if dist <= T.CHASE_STOP_RADIUS * P.SCALE:
        S.chase_time = 0.0
        return segment_angles[0], 0.0, P.TURN_SMOOTHING

    S.chase_time += P.DT
    if S.chase_time <= P.SLOW_DURATION:
        speed = P.BASE_SPEED
    else:
        t = min(1.0, (S.chase_time - P.SLOW_DURATION) / P.RAMP_DURATION)
        speed = P.BASE_SPEED + (P.MAX_SPEED - P.BASE_SPEED) * t ** 3
    proximity = min(1.0, dist / (T.CHASE_SLOWDOWN_RADIUS * P.SCALE))
    rate = P.TURN_SMOOTHING + (1.0 - P.TURN_SMOOTHING) * (1.0 - proximity)
    return math.atan2(dy, dx), speed, rate


def _steer_evade(head, now):
    mx, my = win_utils.cursor_pos()
    dx, dy = head[0] - mx, head[1] - my
    dist = math.hypot(dx, dy)
    hold = T.EVADE_HOLD_DIST * P.SCALE
    threat = T.IMMEDIATE_THREAT_DIST * P.SCALE

    if now - S.last_evade_check >= T.EVADE_PATH_COOLDOWN or dist < threat:
        S.last_evade_check = now
        base = math.atan2(dy, dx) if dist > 1e-5 else segment_angles[0]
        S.locked_evade_angle = base + math.sin(now * 1.4) * (math.pi / 4.0)

    if now - S.evade_speed_last_check >= T.EVADE_SPEED_COOLDOWN or dist < threat:
        S.evade_speed_last_check = now
        if dist < hold:
            S.locked_evade_speed = P.MAX_SPEED * 0.90
        elif dist < P.EVADE_THREAT_DIST:
            S.locked_evade_speed = P.MAX_SPEED * 0.50
        else:
            S.locked_evade_speed = P.WANDER_SPEED * 1.1

    blend = 0.25 if S.locked_evade_speed > S.current_evade_speed else 0.03
    S.current_evade_speed += (S.locked_evade_speed - S.current_evade_speed) * blend

    S.chase_time = 0.0
    rate = 0.25 - 0.16 * min(1.0, dist / threat)
    return S.locked_evade_angle, S.current_evade_speed, rate


_STEERERS = {"box": _steer_box, "wander": _steer_wander, "chase": _steer_chase, "evade": _steer_evade}


def _edge_avoidance(head, target_angle, speed):
    """Blend the heading away from screen edges (wander/evade only)."""
    m = P.SPAWN_MARGIN
    vw, vh = win_utils.VW, win_utils.VH
    sx = sy = 0.0
    if head[0] < m:
        sx += (m - head[0]) / m
    elif head[0] > vw - m:
        sx -= (head[0] - (vw - m)) / m
    if head[1] < m:
        sy += (m - head[1]) / m
    elif head[1] > vh - m:
        sy -= (head[1] - (vh - m)) / m

    if (sx or sy) and speed > 0.0:
        weight = min(1.0, math.hypot(sx, sy))
        target_angle += _angle_diff(math.atan2(sy, sx), target_angle) * weight
    return target_angle


def update_motion(now):
    """Pick this frame's steering for the active mode and move the head."""
    head = segments[0]
    if S.dash_active:
        angle, speed, rate = _steer_dash(head, now)
    else:
        angle, speed, rate = _STEERERS[S.mode](head, now)
        if S.mode in ("wander", "evade"):
            angle = _edge_avoidance(head, angle, speed)

    # idle tracking drives the low-FPS mode in main
    if speed > 0.0:
        S.idle_start = None
    elif S.idle_start is None:
        S.idle_start = now

    if speed <= 0.0:
        return

    # Only a real chase gets the unlimited turn / cursor clamp (a dash during chase must not)
    chasing = S.mode == "chase" and not S.dash_active
    cur = segment_angles[0]
    max_turn = math.pi if chasing else P.MAX_BEND_RAD * 0.75
    turn = max(-max_turn, min(max_turn, _angle_diff(angle, cur) * rate))
    new_angle = cur + turn
    segment_angles[0] = new_angle

    step = speed * P.DT * 60.0
    if chasing:
        cx, cy = win_utils.cursor_pos()
        step = min(step, max(1.0, math.hypot(cx - head[0], cy - head[1]) - T.CHASE_STOP_RADIUS * P.SCALE))
    head[0] += math.cos(new_angle) * step
    head[1] += math.sin(new_angle) * step
