import ctypes
import unittest
from ctypes import wintypes
from native_window import handle_native_frame


class NativeCloseTests(unittest.TestCase):
    def test_caption_paint_is_owned_by_qt(self):
        message = wintypes.MSG()
        for event, expected in ((0x0085, (True, 0)), (0x0086, (True, 1))):
            message.message = event
            self.assertEqual(handle_native_frame(ctypes.addressof(message)), expected)

    def test_client_rect_is_preserved_for_both_nccalcsize_forms(self):
        from unittest.mock import patch, MagicMock
        for full_parameters in (False, True):
            rect = wintypes.RECT(10, 20, 1010, 820)
            message = wintypes.MSG()
            message.message = 0x0083
            message.wParam = full_parameters
            message.lParam = ctypes.addressof(rect)
            user = MagicMock()
            user.IsZoomed.return_value = False
            with patch('native_window.ctypes.WinDLL', return_value=user):
                self.assertEqual(handle_native_frame(ctypes.addressof(message)), (True, 0))
            self.assertEqual((rect.left, rect.top, rect.right, rect.bottom), (10, 20, 1010, 820))

    def test_only_confirmed_close_prevents_premature_hide(self):
        class Position(ctypes.Structure):
            _fields_=[('hwnd',wintypes.HWND),('after',wintypes.HWND),('x',ctypes.c_int),
                      ('y',ctypes.c_int),('cx',ctypes.c_int),('cy',ctypes.c_int),('flags',wintypes.UINT)]
        position=Position()
        position.flags=0x0080|0x0010|0x0001
        message=wintypes.MSG()
        message.message=0x0046
        message.lParam=ctypes.addressof(position)
        handle_native_frame(ctypes.addressof(message),False)
        self.assertEqual(position.flags,0x0080|0x0010|0x0001)
        handle_native_frame(ctypes.addressof(message),True)
        self.assertEqual(position.flags,0x0010|0x0001)


if __name__ == '__main__':
    unittest.main()
