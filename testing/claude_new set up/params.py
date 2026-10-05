"""Runtime parameters. P holds every config.py constant; apply_scale() overwrites
the size-dependent ones for the current phase. Replaces the old
`globals().update(scaled_params(...))` trick, which can't work across modules."""
from types import SimpleNamespace

import config

P = SimpleNamespace(**{k: v for k, v in vars(config).items() if k.isupper()})
P.SCALE = 1.0


def apply_scale(scale):
    for key, value in config.scaled_params(scale).items():
        setattr(P, key, value)
