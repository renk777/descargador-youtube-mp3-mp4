"""Per-window Acrylic composition for Qt's translucent Windows surface."""
import ctypes
import sys
from ctypes import wintypes


class AccentPolicy(ctypes.Structure):
    _fields_ = [('state', ctypes.c_int), ('flags', ctypes.c_int),
                ('gradient', wintypes.DWORD), ('animation', ctypes.c_int)]


class CompositionData(ctypes.Structure):
    _fields_ = [('attribute', ctypes.c_int), ('data', ctypes.c_void_p),
                ('size', ctypes.c_size_t)]


def set_acrylic_active(window_id: int, active: bool) -> tuple[bool, str]:
    if sys.platform != 'win32' or sys.getwindowsversion().build < 17134:
        return False, 'Acrylic no está disponible en este sistema'
    try:
        user = ctypes.WinDLL('user32', use_last_error=True)
        apply = user.SetWindowCompositionAttribute
        apply.argtypes = [wintypes.HWND, ctypes.POINTER(CompositionData)]
        apply.restype = wintypes.BOOL
        # AABBGGRR: native blur with a translucent charcoal tint, never window opacity.
        policy = AccentPolicy(4 if active else 0, 0, 0x99251f1f if active else 0, 0)
        data = CompositionData(19, ctypes.cast(ctypes.pointer(policy), ctypes.c_void_p), ctypes.sizeof(policy))
        result = apply(wintypes.HWND(window_id), ctypes.byref(data))
        return bool(result), ('Acrylic nativo' if result else f'Windows no pudo aplicar Acrylic ({ctypes.get_last_error()})')
    except (OSError, AttributeError) as error:
        return False, str(error)


def enable_acrylic(window_id: int) -> tuple[bool, str]:
    if sys.platform != 'win32':
        return False, 'Acrylic requiere Windows'
    try:
        dwm = ctypes.WinDLL('dwmapi')
        dwm.DwmSetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
        dwm.DwmSetWindowAttribute.restype = ctypes.c_long
        hwnd = wintypes.HWND(window_id)
        class BlurBehind(ctypes.Structure):
            _fields_ = [('flags', wintypes.DWORD), ('enabled', wintypes.BOOL),
                        ('region', wintypes.HRGN), ('transition', wintypes.BOOL)]
        class Margins(ctypes.Structure):
            _fields_ = [('left', ctypes.c_int), ('right', ctypes.c_int),
                        ('top', ctypes.c_int), ('bottom', ctypes.c_int)]
        # Opt Qt's alpha surface into DWM composition before installing its accent policy.
        dwm.DwmEnableBlurBehindWindow.argtypes = [wintypes.HWND, ctypes.POINTER(BlurBehind)]
        dwm.DwmEnableBlurBehindWindow.restype = ctypes.c_long
        blur = BlurBehind(1, True, None, False)
        dwm.DwmEnableBlurBehindWindow(hwnd, ctypes.byref(blur))
        if sys.getwindowsversion().build >= 22000:
            dwm.DwmExtendFrameIntoClientArea.argtypes = [wintypes.HWND, ctypes.POINTER(Margins)]
            dwm.DwmExtendFrameIntoClientArea.restype = ctypes.c_long
            dwm.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(Margins(-1, -1, -1, -1)))
        for attribute, value in ((20, 1), (33, 2), (38, 1)):
            # Disable the previous system backdrop, which can hide the accent surface.
            number = ctypes.c_int(value)
            dwm.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(number), ctypes.sizeof(number))
        return set_acrylic_active(window_id, True)
    except (OSError, AttributeError) as error:
        return False, str(error)
