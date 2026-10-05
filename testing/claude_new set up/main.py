import sys
import time
import tkinter as tk

import win_utils
import tuning as T
from assets import head_img, init_assets
from chain import relax, spawn_worm
from death import update_dying
from destruction import DestructionAnimator
from effects import Particles
from hotkeys import MODE_CHORDS, PHASE_CHORD
from movement import update_motion
from params import P
from phase import dash_finished, finish_phase_change, start_phase_change
from render import WormRenderer
from speech import Speech
from state import S

# --- Window ---
root = tk.Tk()
root.title("Worm")
root.overrideredirect(True)
root.attributes("-topmost", True)
root.attributes("-transparentcolor", T.KEY)
root.geometry(f"{win_utils.VW}x{win_utils.VH}{win_utils.VX:+d}{win_utils.VY:+d}")
root.config(bg=T.KEY)

init_assets()  # ImageTk objects need the root to exist

canvas = tk.Canvas(root, bg=T.KEY, highlightthickness=0, bd=0)
canvas.pack(fill="both", expand=True)
root.update()

HWND = win_utils.user32.GetParent(root.winfo_id()) or root.winfo_id()
win_utils.make_click_through(HWND)
win_utils.keep_on_top(HWND)

# --- Components (creation order = stacking order: worm < speech < particles) ---
animator = DestructionAnimator(
    P.SEGMENT_SIZE, P.NUM_SEGMENTS, P.DESTROY_DURATION,
    deteriorate_delay=P.DETERIORATE_DELAY,
    deteriorate_duration=P.DETERIORATE_DURATION,
)
spawn_worm()
renderer = WormRenderer(canvas, animator)
speech = Speech(canvas)
particles = Particles(canvas)
tray_icon = None


def request_quit():
    if not S.quit_flag:
        S.quit_flag = True
        animator.start()
        if tray_icon:
            tray_icon.stop()


def update_step():
    S.tick += 1
    if win_utils.hotkey_pressed():
        request_quit()

    if not S.quit_flag:
        for mode, chord in MODE_CHORDS.items():
            if chord.pressed():
                S.toggle_mode(mode)
        if PHASE_CHORD.pressed() and not S.dash_active:
            start_phase_change()

        now = time.time()
        update_motion(now)
        relax(P.MAX_BEND_RAD)
        if S.dash_active and dash_finished(now):
            finish_phase_change(animator, speech)
    elif P.BREAK_APART:
        update_dying(animator, particles)

    speech.update(S.quit_flag or animator.is_destroying or S.dash_active)
    particles.update()
    renderer.draw()


# --- Tray icon ---
try:
    import pystray

    tray_icon = pystray.Icon(
        "worm", head_img.resize((64, 64)), "Worm",
        menu=pystray.Menu(pystray.MenuItem("Quit", lambda icon, item: request_quit())),
    )
    tray_icon.run_detached()
except Exception:
    pass

# --- Main loop ---
last_topmost = time.time()
while not animator.is_finished:
    loop_start = time.time()
    try:
        update_step()
        root.update()

        if loop_start - last_topmost > 2.0:
            win_utils.keep_on_top(HWND)
            last_topmost = loop_start

        idle = (not S.quit_flag and S.idle_start is not None
                and loop_start - S.idle_start > P.IDLE_THRESHOLD)
        target_ms = P.IDLE_FPS_MS if idle else P.FPS_MS
        time.sleep(max(0.001, target_ms / 1000.0 - (time.time() - loop_start)))
    except KeyboardInterrupt:
        request_quit()
    except tk.TclError:
        break

try:
    root.destroy()
except Exception:
    pass
sys.exit(0)
