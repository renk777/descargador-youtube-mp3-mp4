"""Native window integration; no changes to Windows or Windhawk preferences."""
import ctypes
import sys
from ctypes import wintypes


def configure_native_window(hwnd):
    if sys.platform != 'win32':
        return False
    user = ctypes.WinDLL('user32', use_last_error=True)
    getter = user.GetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p) == 8 else user.GetWindowLongW
    setter = user.SetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p) == 8 else user.SetWindowLongW
    getter.argtypes = [wintypes.HWND, ctypes.c_int]
    getter.restype = ctypes.c_ssize_t
    setter.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
    setter.restype = ctypes.c_ssize_t
    style = getter(hwnd, -16)
    # Caption, system menu, thick frame and min/max boxes: ordinary app-window semantics.
    setter(hwnd, -16, style | 0x00C00000 | 0x00080000 | 0x00040000 | 0x00020000 | 0x00010000)
    dwm = ctypes.WinDLL('dwmapi')
    dwm.DwmSetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
    dwm.DwmSetWindowAttribute.restype = ctypes.c_long
    enabled = wintypes.BOOL(False)
    dwm.DwmSetWindowAttribute(hwnd, 3, ctypes.byref(enabled), ctypes.sizeof(enabled))
    # Flush the frame metrics cached before changing the styles.
    user.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                  ctypes.c_int, ctypes.c_int, wintypes.UINT]
    user.SetWindowPos(hwnd, None, 0, 0, 0, 0, 0x0020 | 0x0001 | 0x0002 | 0x0004 | 0x0010)
    return True


def handle_native_frame(message, closing=False):
    """Keep the custom title bar while retaining a real native top-level frame."""
    msg = wintypes.MSG.from_address(int(message))
    if closing and msg.message == 0x0046:  # WM_WINDOWPOSCHANGING
        class WindowPos(ctypes.Structure):
            _fields_ = [('hwnd', wintypes.HWND), ('after', wintypes.HWND),
                        ('x', ctypes.c_int), ('y', ctypes.c_int), ('cx', ctypes.c_int),
                        ('cy', ctypes.c_int), ('flags', wintypes.UINT)]
        position = WindowPos.from_address(msg.lParam)
        # QWindow.destroy() first requests a hide. Keep the HWND visible until
        # Qt's actual DestroyWindow call so animation hooks can take a snapshot.
        position.flags &= ~0x0080  # SWP_HIDEWINDOW
        return None
    if msg.message == 0x0085:  # WM_NCPAINT: Qt paints the complete caption.
        return True, 0
    if msg.message == 0x0086:  # WM_NCACTIVATE: no second caption on activation.
        return True, 1
    if msg.message == 0x0083:  # WM_NCCALCSIZE
        # The first member of NCCALCSIZE_PARAMS is the proposed window RECT.
        rect = wintypes.RECT.from_address(msg.lParam)
        user = ctypes.WinDLL('user32')
        user.IsZoomed.argtypes = [wintypes.HWND]
        user.IsZoomed.restype = wintypes.BOOL
        if user.IsZoomed(msg.hWnd):
            class MonitorInfo(ctypes.Structure):
                _fields_ = [('size', wintypes.DWORD), ('monitor', wintypes.RECT),
                            ('work', wintypes.RECT), ('flags', wintypes.DWORD)]
            user.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
            user.MonitorFromWindow.restype = wintypes.HANDLE
            user.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MonitorInfo)]
            user.GetMonitorInfoW.restype = wintypes.BOOL
            info = MonitorInfo()
            info.size = ctypes.sizeof(info)
            if user.GetMonitorInfoW(user.MonitorFromWindow(msg.hWnd, 2), ctypes.byref(info)):
                rect.left, rect.top, rect.right, rect.bottom = info.work.left, info.work.top, info.work.right, info.work.bottom
        return True, 0
    return None
