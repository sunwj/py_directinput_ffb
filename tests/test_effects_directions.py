import unittest

import ctypes as C

from directinput_ffb.dinput_definitions import (
    DIEFFECT,
    DICONSTANTFORCE,
    DIEFF_CARTESIAN,
    DIEFF_POLAR,
    DIENVELOPE,
    DIEP_DIRECTION,
    DIEP_GAIN,
)
from directinput_ffb.dinput_effects import (
    EffectHandle,
    _build_effect_description,
)


class TestDirectionRewrite(unittest.TestCase):
    def _handle(self, axes_offsets, basis):
        n = len(axes_offsets)
        axes = (C.c_uint * n)(*axes_offsets)
        directions = (C.c_long * n)(0) if n == 1 else (C.c_long * n)(0, 0)
        return EffectHandle(
            effect=None,
            dieffect=DIEFFECT(),
            axes=axes,
            directions=directions,
            type_specific=DICONSTANTFORCE(),
            direction_basis=basis,
        )

    def test_cartesian_90(self):
        h = self._handle((0, 4), DIEFF_CARTESIAN)
        h._set_direction(9000)
        self.assertEqual(list(h.directions), [32767, 0])

    def test_polar(self):
        h = self._handle((0, 4), DIEFF_POLAR)
        h._set_direction(9000)
        self.assertEqual(list(h.directions), [9000, 0])

    def test_one_axis(self):
        h = self._handle((0,), DIEFF_POLAR)
        h._set_direction(9000)
        self.assertEqual(list(h.directions), [0])

    def test_one_axis_zero_deg_projects_zero(self):
        h = self._handle((0,), DIEFF_POLAR)
        h._set_direction(0)
        self.assertEqual(list(h.directions), [0])


class TestEnvelopeBuild(unittest.TestCase):
    def test_envelope_wired(self):
        env = DIENVELOPE()
        env.dwSize = C.sizeof(DIENVELOPE)
        env.dwAttackLevel = 0
        env.dwAttackTime = 200 * 1000
        env.dwFadeLevel = 0
        env.dwFadeTime = 200 * 1000
        desc, _axes, _directions = _build_effect_description(
            axes_offsets=(0, 4),
            direction_hundredths_deg=0,
            direction_basis=DIEFF_CARTESIAN,
            duration_us=1_000_000,
            type_specific=DICONSTANTFORCE(),
            envelope=env,
        )
        self.assertIsNotNone(desc.lpEnvelope)
        self.assertEqual(desc.lpEnvelope.contents.dwAttackTime, 200000)

    def test_apply_builds_flags_safely(self):
        h = EffectHandle(
            effect=None,
            dieffect=DIEFFECT(),
            axes=(C.c_uint * 2)(0, 4),
            directions=(C.c_long * 2)(0, 0),
            type_specific=DICONSTANTFORCE(),
            direction_basis=DIEFF_CARTESIAN,
        )
        # apply() must fail only at the COM call (effect=None); _set_direction must
        # already have rewritten the array before that, or pgather general calls.
        with self.assertRaises(AttributeError):
            h.apply(direction_hundredths_deg=9000, gain=8000, duration_ms=500)
        self.assertEqual(list(h.directions), [32767, 0])

    def test_apply_only_sets_requested_flags(self):
        class FakeEffect:
            def __init__(self):
                self.flags = None

            def SetParameters(self, _desc, flags):
                self.flags = flags
                return 0

        effect = FakeEffect()
        h = EffectHandle(
            effect=effect,
            dieffect=DIEFFECT(),
            axes=(C.c_uint * 2)(0, 4),
            directions=(C.c_long * 2)(0, 0),
            type_specific=DICONSTANTFORCE(),
            direction_basis=DIEFF_CARTESIAN,
        )
        h.apply(direction_hundredths_deg=9000, gain=8000)
        self.assertEqual(effect.flags, DIEP_DIRECTION | DIEP_GAIN)


if __name__ == "__main__":
    unittest.main()
