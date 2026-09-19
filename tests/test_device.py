import unittest

from directinput_ffb_tester.device import (
    DeviceSession,
    select_condition_axes,
    normalize,
)
from directinput_ffb.dinput_definitions import DIJOFS_X, DIJOFS_Y


class TestNormalize(unittest.TestCase):
    def test_signed_range(self):
        self.assertEqual(normalize(0, -10000, 10000), 0.0)
        self.assertEqual(normalize(-10000, -10000, 10000), -1.0)
        self.assertEqual(normalize(10000, -10000, 10000), 1.0)

    def test_unsigned_range(self):
        self.assertAlmostEqual(normalize(32767, 0, 65535), 0.0, places=4)
        self.assertAlmostEqual(normalize(0, 0, 65535), -1.0, places=4)
        self.assertAlmostEqual(normalize(65535, 0, 65535), 1.0, places=4)

    def test_degenerate(self):
        self.assertEqual(normalize(123, 50, 50), 0.0)


class TestConditionAxes(unittest.TestCase):
    def test_two_axis(self):
        self.assertEqual(
            select_condition_axes(True, True, True, True, [DIJOFS_X, DIJOFS_Y]),
            [DIJOFS_X, DIJOFS_Y])

    def test_wheel_no_pitch(self):
        self.assertEqual(select_condition_axes(True, True, True, False, [DIJOFS_X]),
                         [DIJOFS_X])

    def test_both_off_selects_no_axis(self):
        self.assertEqual(select_condition_axes(False, False, True, True, [DIJOFS_X]),
                         [])

    def test_unavailable_requested_axis_does_not_fallback(self):
        self.assertEqual(select_condition_axes(False, True, True, False, [DIJOFS_X]),
                         [])

    def test_y_only_condition_uses_y_offset(self):
        from directinput_ffb_tester.spec import EffectSpec, FfbEffect

        session = DeviceSession()
        session.ffb_axes = [DIJOFS_Y]
        spec = EffectSpec(
            effect=FfbEffect.SPRING,
            apply_roll=False,
            apply_pitch=True,
            center_offset_x=111,
            center_offset_y=222,
        )
        conditions = session._live_condition_array(spec)
        self.assertEqual(conditions[0].lOffset, 222)


class TestNoDevice(unittest.TestCase):
    def test_enumerate_returns_list(self):
        s = DeviceSession()
        self.assertIsInstance(s.enumerate(), list)

    def test_poll_not_connected(self):
        s = DeviceSession()
        p = s.poll()
        self.assertFalse(p.ok)
        self.assertFalse(s.connected)


class TestEffectValidation(unittest.TestCase):
    def test_periodic_magnitude_and_offset_must_fit_nominal_range(self):
        from directinput_ffb_tester.spec import EffectSpec, FfbEffect

        session = DeviceSession()
        spec = EffectSpec(
            effect=FfbEffect.SINE,
            magnitude=8000,
            periodic_offset=3000,
        )
        with self.assertRaises(ValueError):
            session._live_type_specific(spec)


if __name__ == "__main__":
    unittest.main()
