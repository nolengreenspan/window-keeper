"""Window Keeper: keeps ordinary windows from hanging under the taskbar.

Every few seconds it looks at each open window. If the bottom of a window sits
below the usable area of its screen (the part the taskbar does not cover), it
moves the window up by exactly that much. It never resizes anything, never
touches maximized, minimized or full-screen windows, and leaves a window alone
while the left mouse button is held down, so dragging is never fought.

    pythonw window_keeper.py            run quietly in the background
    python  window_keeper.py --once     fix once, print what moved, then exit
"""

import ctypes
import ctypes.wintypes as wt
import sys
import time

CHECK_EVERY = 2.0          # seconds between looks
MIN_WIDTH = 300            # ignore tiny pop-ups and tool windows

user32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi
kernel32 = ctypes.windll.kernel32

DWMWA_EXTENDED_FRAME_BOUNDS = 9
DWMWA_CLOAKED = 14
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
MONITOR_DEFAULTTONEAREST = 2
SWP_NOSIZE, SWP_NOZORDER, SWP_NOACTIVATE = 0x0001, 0x0004, 0x0010
VK_LBUTTON = 0x01
SKIP_CLASSES = {"Shell_TrayWnd", "Shell_SecondaryTrayWnd", "Progman", "WorkerW",
                "NotifyIconOverflowWindow", "TopLevelWindowForOverflowXamlIsland"}


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("rcMonitor", wt.RECT),
                ("rcWork", wt.RECT), ("dwFlags", wt.DWORD)]


ENUM = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
user32.MonitorFromWindow.restype = wt.HMONITOR
user32.MonitorFromWindow.argtypes = [wt.HWND, wt.DWORD]


def title_of(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(hwnd, buf, 256)
    return buf.value


def class_of(hwnd):
    buf = ctypes.create_unicode_buffer(128)
    user32.GetClassNameW(hwnd, buf, 128)
    return buf.value


def visible_rect(hwnd):
    """The window as the eye sees it, without Windows' invisible resize border."""
    rect = wt.RECT()
    if dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_EXTENDED_FRAME_BOUNDS,
                                    ctypes.byref(rect), ctypes.sizeof(rect)) != 0:
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return rect


def candidate(hwnd):
    """True for an ordinary, visible, normal-state window worth checking."""
    if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd) or user32.IsZoomed(hwnd):
        return False
    cloaked = ctypes.c_int(0)
    dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, ctypes.byref(cloaked), 4)
    if cloaked.value:
        return False
    ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    if ex & (WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE):
        return False
    if not title_of(hwnd) or class_of(hwnd) in SKIP_CLASSES:
        return False
    return True


def nudge(hwnd):
    """Move one window up if it hangs below its screen's usable area.
    Returns the number of pixels moved, or 0."""
    vis = visible_rect(hwnd)
    if vis.right - vis.left < MIN_WIDTH:
        return 0
    info = MONITORINFO()
    info.cbSize = ctypes.sizeof(MONITORINFO)
    monitor = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
    if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
        return 0
    work, full = info.rcWork, info.rcMonitor
    # Full-screen windows (video, games) cover the whole screen on purpose.
    if (vis.left <= full.left and vis.right >= full.right
            and vis.top <= full.top and vis.bottom >= full.bottom):
        return 0
    over = vis.bottom - work.bottom
    if over <= 0:
        return 0
    # A window taller than the usable area cannot fit; leave it alone.
    if vis.bottom - vis.top > work.bottom - work.top:
        return 0
    # Never lift the top edge above the screen.
    over = min(over, vis.top - work.top)
    if over <= 0:
        return 0
    outer = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(outer))
    user32.SetWindowPos(hwnd, 0, outer.left, outer.top - over, 0, 0,
                        SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE)
    return over


def sweep():
    moved = []

    def callback(hwnd, _lparam):
        try:
            if candidate(hwnd):
                pixels = nudge(hwnd)
                if pixels:
                    moved.append((title_of(hwnd), pixels))
        except Exception:
            pass
        return True

    user32.EnumWindows(ENUM(callback), 0)
    return moved


def single_instance():
    """True if this is the only copy running."""
    kernel32.CreateMutexW(None, False, "Local\\WindowKeeperSingleInstance")
    return kernel32.GetLastError() != 183  # ERROR_ALREADY_EXISTS


def main():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        user32.SetProcessDPIAware()

    if "--once" in sys.argv:
        for name, pixels in sweep():
            print("moved up %d px: %s" % (pixels, name))
        return

    if not single_instance():
        return
    while True:
        # Do nothing while the mouse button is down, so a drag is never fought.
        if not (user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000):
            sweep()
        time.sleep(CHECK_EVERY)


if __name__ == "__main__":
    main()
