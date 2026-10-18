"""Dying animation: head crawls and writhes, segments pop off with an explosion."""
import math
import random
import time

import tuning as T
from chain import NUM_SEGMENTS, broken_physics, draw_angles, relax, segment_angles, segments
from params import P
from state import S


def _detach(i, particles):
    p = broken_physics[i]
    ang = random.uniform(0, math.tau)
    force = P.BREAK_POP_FORCE * random.uniform(0.5, 1.0)
    p.update(detached=True, detach_time=time.time(),
             vx=math.cos(ang) * force, vy=math.sin(ang) * force,
             rot=draw_angles[i], rot_speed=random.uniform(-12.0, 12.0))
    particles.explode(segments[i][0], segments[i][1])


def update_dying(animator, particles):
    frame = P.DT * 60.0

    if not broken_physics[0]["detached"]:
        t = animator.elapsed
        decay = math.exp(-T.DEATH_CRAWL_DECAY * t)
        segment_angles[0] += (S.death_curl_dir * T.DEATH_CURL
                              + math.sin(t * T.DEATH_WRITHE_FREQ) * T.DEATH_WRITHE_AMOUNT * 0.3) * decay
        step = T.DEATH_CRAWL_SPEED * P.SCALE * decay * frame
        segments[0][0] += math.cos(segment_angles[0]) * step
        segments[0][1] += math.sin(segment_angles[0]) * step

    for i in range(NUM_SEGMENTS):
        p = broken_physics[i]
        if not p["detached"]:
            if animator.is_segment_started(i):
                _detach(i, particles)
                animator.mark_detached(i)
        else:  # flying debris
            p["vy"] += P.DYING_GRAVITY * frame
            segments[i][0] += p["vx"] * frame
            segments[i][1] += p["vy"] * frame
            p["rot"] += p["rot_speed"] * frame

    relax(P.MAX_BEND_RAD, attached_only=True)
