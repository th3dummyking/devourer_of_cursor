import ctypes

user32 = ctypes.windll.user32

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        user32.SetProcessDPIAware()
    except Exception:
        pass

VX = user32.GetSystemMetrics(76)
VY = user32.GetSystemMetrics(77)
VW = user32.GetSystemMetrics(78)
VH = user32.GetSystemMetrics(79)

GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x20
WS_EX_LAYERED = 0x80000
WS_EX_TOOLWINDOW = 0x80
WS_EX_NOACTIVATE = 0x08000000
HWND_TOPMOST = -1
SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE = 0x1, 0x2, 0x10


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def cursor_pos():
    p = POINT()
    user32.GetCursorPos(ctypes.byref(p))
    return p.x - VX, p.y - VY


def make_click_through(hwnd):
    style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    style |= WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)


def keep_on_top(hwnd):
    user32.SetWindowPos(
        hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE
    )


def is_key_down(vk):
    return bool(user32.GetAsyncKeyState(vk) & 0x8000)


def hotkey_pressed():
    return is_key_down(0x11) and is_key_down(0x12) and is_key_down(0x51)  # Ctrl+Alt+Q


def phase_hotkey_down():
    return is_key_down(0x11) and is_key_down(0x12) and is_key_down(0x50)  # Ctrl+Alt+P
