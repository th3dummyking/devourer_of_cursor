"""Tunable constants that used to live at the top of main.py.
Edit these freely; config.py keeps the original/scaled values."""
import win_utils

KEY = "#010101"  # transparent colour key

# --- Wander mode: corner boxes (fraction of screen) ---
CORNER_WIDTH_RATIO = 0.15
CORNER_HEIGHT_RATIO = 0.15

# --- Box / circuit mode: TL -> TR -> BR -> BL ---
MARGIN = -5
CIRCUIT_WAYPOINTS = [
    (MARGIN, MARGIN),
    (win_utils.VW - MARGIN, MARGIN),
    (win_utils.VW - MARGIN, win_utils.VH - MARGIN),
    (MARGIN, win_utils.VH - MARGIN),
]
CIRCUIT_ARRIVE_DIST = 80.0
CIRCUIT_SPEED_MULTIPLIER = 0.8
CIRCUIT_STEER_RATE = 0.30
BODY_FOLLOW_STIFFNESS = 1.0  # 0.2 = soft body, 1.0 = sharp follow
WAVE_ENABLED = True
WAVE_FREQUENCY = 4.5
WAVE_AMPLITUDE = 0.9  # radians

# --- Chase mode ---
CHASE_STOP_RADIUS = 25.0
CHASE_SLOWDOWN_RADIUS = 200.0

# --- Evade mode ---
EVADE_PATH_COOLDOWN = 0.8
EVADE_SPEED_COOLDOWN = 0.5
EVADE_HOLD_DIST = 150.0
IMMEDIATE_THREAT_DIST = 20.0

# --- Phase change (Ctrl+Alt+P) ---
PHASE_DASH_TIMEOUT = 4.0         # failsafe, seconds
PHASE_DASH_TURN_PENALTY = 900.0  # higher = prefers the edge it already faces
SPEECH_STATE_SWITCH_DELAY = 0.5

# --- Death animation ---
DEATH_CRAWL_SPEED = 1.2
DEATH_CRAWL_DECAY = 0.8
DEATH_CURL = 0.2
DEATH_WRITHE_FREQ = 16.0
DEATH_WRITHE_AMOUNT = 0.2

# --- Explosion particles ---
EXPLOSION_OPACITY = 0.7
EXPLOSION_PIXEL = 5
EXPLOSION_PARTICLES = 4
EXPLOSION_SPEED = (2.0, 4.0)
EXPLOSION_SIZE = (20.0, 44.0)
EXPLOSION_LIFE = (0.5, 0.8)
EXPLOSION_FLASH_SIZE = 20.0 # the white flash size
EXPLOSION_GRAVITY = 0.35  # was used but never defined
EXPLOSION_COLORS = ["#c9a7ff", "#7df9ff", "#a855f7", "#ffffff"]
# (min opacity, stipple pattern), checked top to bottom
STIPPLE_LEVELS = [(0.88, ""), (0.62, "gray75"), (0.37, "gray50"), (0.18, "gray25"), (0.0, "gray12")]
