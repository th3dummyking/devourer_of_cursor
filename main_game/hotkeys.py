"""Edge-triggered key chords (fire once per press)."""
import win_utils


class Chord:
    def __init__(self, is_down):
        self._is_down = is_down
        self._was_down = False

    def pressed(self):
        down = self._is_down()
        edge = down and not self._was_down
        self._was_down = down
        return edge


def key_combo(*vks):
    return Chord(lambda: all(win_utils.is_key_down(vk) for vk in vks))


MODE_CHORDS = {
    "wander": key_combo(0x57, 0x4D, 0x11),  # W + M + ctrl
    "chase": key_combo(0x43, 0x4D, 0x11),   # C + M + ctrl
    "box": key_combo(0x52, 0x11, 0x12),     # ctrl + alt + R
}
PHASE_CHORD = Chord(win_utils.phase_hotkey_down)  # Ctrl+Alt+P
