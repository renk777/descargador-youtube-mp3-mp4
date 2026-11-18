import ctypes
import unittest
from ctypes import wintypes
from native_window import handle_native_frame


class NativeCloseTests(unittest.TestCase):
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
