import ctypes
import json
import sys
import time
from ctypes import wintypes as w

u = ctypes.windll.user32
u.SetProcessDPIAware()
u.GetWindowThreadProcessId.argtypes = [w.HWND, ctypes.POINTER(w.DWORD)]
u.GetWindowTextW.argtypes = [w.HWND, w.LPWSTR, ctypes.c_int]
u.GetWindowLongW.argtypes = [w.HWND, ctypes.c_int]
u.IsWindowVisible.argtypes = [w.HWND]
u.ShowWindow.argtypes = [w.HWND, ctypes.c_int]
u.SetWindowPos.argtypes = [w.HWND, w.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, w.UINT]
u.GetWindowRect.argtypes = [w.HWND, ctypes.POINTER(w.RECT)]
target = int(sys.argv[1])
matches = []
def visit(hwnd, _):
    pid = w.DWORD()
    title = ctypes.create_unicode_buffer(512)
    u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    u.GetWindowTextW(hwnd, title, 512)
    if pid.value == target and 'Gradient' in title.value and u.IsWindowVisible(hwnd):
        matches.append(hwnd)
    return True
callback = ctypes.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)(visit)
u.EnumWindows(callback, 0)
assert len(matches) == 1, matches
hwnd = matches[0]
def healthy():
    return bool(u.IsWindowVisible(hwnd)) and bool(u.GetWindowLongW(hwnd, -20) & 8)
assert healthy(), 'Deployed window must be visible and topmost'
u.SetWindowPos(hwnd, w.HWND(-2), 0, 0, 0, 0, 0x13)
u.ShowWindow(hwnd, 0)
deadline = time.monotonic() + 5
while not healthy() and time.monotonic() < deadline:
    time.sleep(0.1)
assert healthy(), 'Visibility did not recover'
rect = w.RECT()
u.GetWindowRect(hwnd, ctypes.byref(rect))
print(json.dumps(dict(pid=target, hwnd=hwnd, visible=True, topmost=True, recovery='passed', bounds=[rect.left, rect.top, rect.right, rect.bottom])))
