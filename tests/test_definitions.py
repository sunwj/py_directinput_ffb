import ctypes as C
import unittest

from directinput_ffb.dinput_definitions import (
    DIPROPDWORD,
    DIPROP_FFGAIN,
    DIPROP_AUTOCENTER,
    DIPROPAUTOCENTER_OFF,
    SFFC_STOPALL,
    DIEP_STARTDELAY,
    DIEP_ALLPARAMS,
)

import directinput_ffb


class TestDefinitions(unittest.TestCase):
    def test_dipropdword_size(self):
        self.assertEqual(C.sizeof(DIPROPDWORD), 20)

    def test_prop_ids(self):
        self.assertEqual(int(DIPROP_FFGAIN.value), 7)
        self.assertEqual(int(DIPROP_AUTOCENTER.value), 9)
        self.assertEqual(DIPROPAUTOCENTER_OFF, 0)

    def test_ffb_constants(self):
        self.assertEqual(SFFC_STOPALL, 0x00000002)
        self.assertEqual(DIEP_STARTDELAY, 0x00000200)
        self.assertEqual(DIEP_ALLPARAMS, 0x000003FF)


class TestDeviceHelpers(unittest.TestCase):
    def test_exports(self):
        self.assertTrue(callable(directinput_ffb.get_device_gain))
        self.assertTrue(callable(directinput_ffb.set_device_gain))
        self.assertTrue(callable(directinput_ffb.set_autocenter))
        self.assertTrue(callable(directinput_ffb.stop_all_effects))


if __name__ == "__main__":
    unittest.main()
