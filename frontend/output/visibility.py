import ctypes
import json
from ctypes import wintypes as w

u = ctypes.windll.user32
u.SetProcessDPIAware()
u.GetWindowRect.argtypes = [w.HWND, ctypes.POINTER(w.RECT)]
u.GetWindowThreadProcessId.argtypes = [w.HWND, ctypes.POINTER(w.DWORD)]
u.IsWindowVisible.argtypes = [w.HWND]
u.IsIconic.argtypes = [w.HWND]
u.GetWindowTextW.argtypes = [w.HWND, w.LPWSTR, ctypes.c_int]
u.GetForegroundWindow.restype = w.HWND
rows = []
def visit(hwnd, _):
    pid = w.DWORD()
    u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    title = ctypes.create_unicode_buffer(512)
    u.GetWindowTextW(hwnd, title, 512)
    if pid.value == 24788 or 'Codex' in title.value or title.value == 'Gradient':
        rect = w.RECT()
        u.GetWindowRect(hwnd, ctypes.byref(rect))
        cloak = w.DWORD()
        ctypes.windll.dwmapi.DwmGetWindowAttribute(w.HWND(hwnd), 14, ctypes.byref(cloak), 4)
        rows.append(dict(pid=pid.value, hwnd=hwnd, title=title.value, visible=bool(u.IsWindowVisible(hwnd)), minimized=bool(u.IsIconic(hwnd)), cloaked=cloak.value, rect=[rect.left, rect.top, rect.right, rect.bottom]))
    return True
callback = ctypes.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)(visit)
u.EnumWindows(callback, 0)
print(json.dumps(dict(windows=rows, foreground=u.GetForegroundWindow(), virtual_screen=[u.GetSystemMetrics(i) for i in [76,77,78,79]]), indent=2))
