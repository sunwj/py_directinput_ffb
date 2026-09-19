import unittest

from directinput_ffb_tester.spec import (
    FfbEffect,
    EffectSpec,
    ForceModel,
    Kinematics,
    direction_components,
    DirWord,
    Pretty,
)


class TestDirection(unittest.TestCase):
    def test_components(self):
        cx, cy = direction_components(90)
        self.assertAlmostEqual(cx, 1.0, places=9)
        self.assertAlmostEqual(cy, 0.0, places=9)
        cx, cy = direction_components(0)
        self.assertAlmostEqual(cx, 0.0, places=9)
        self.assertAlmostEqual(cy, -1.0, places=9)


class TestForceModel(unittest.TestCase):
    def _spec(self, **kw):
        return EffectSpec(magnitude=4000, **kw)

    def test_constant(self):
        s = self._spec(effect=FfbEffect.CONSTANT_FORCE, direction_deg=90)
        r = ForceModel.evaluate(s, 0, Kinematics())
        self.assertAlmostEqual(r.fx, -4000.0)
        self.assertAlmostEqual(r.fy, 0.0, places=6)
        self.assertAlmostEqual(r.direction_deg, 270.0)

    def test_sine_quarter(self):
        s = self._spec(effect=FfbEffect.SINE, period_ms=1500, direction_deg=0)
        r = ForceModel.evaluate(s, 0.375, Kinematics())
        self.assertAlmostEqual(r.instantaneous, 1.0, places=6)
        self.assertAlmostEqual(r.fy, 4000.0, places=3)
        r0 = ForceModel.evaluate(s, 0.0, Kinematics())
        self.assertAlmostEqual(r0.instantaneous, 0.0, places=9)

    def test_square_triangle(self):
        s = self._spec(effect=FfbEffect.SQUARE, period_ms=1000)
        r = ForceModel.evaluate(s, 0.0, Kinematics())
        self.assertAlmostEqual(r.instantaneous, 1.0, places=9)
        r = ForceModel.evaluate(s, 0.5, Kinematics())
        self.assertAlmostEqual(r.instantaneous, -1.0, places=9)
        s = self._spec(effect=FfbEffect.TRIANGLE, period_ms=1000)
        self.assertAlmostEqual(ForceModel.evaluate(s, 0.0, Kinematics()).instantaneous, -1.0, places=9)
        self.assertAlmostEqual(ForceModel.evaluate(s, 0.5, Kinematics()).instantaneous, 1.0, places=9)

    def test_ramp(self):
        s = EffectSpec(effect=FfbEffect.RAMP_FORCE, ramp_start=0, ramp_end=8000, duration_ms=1500)
        r = ForceModel.evaluate(s, 0.75, Kinematics())
        self.assertAlmostEqual(r.instantaneous, 0.5, places=9)
        self.assertAlmostEqual(r.magnitude, 4000.0, places=6)

    def test_envelope(self):
        s = self._spec(effect=FfbEffect.CONSTANT_FORCE, direction_deg=0,
                       use_envelope=True, attack_level=0, attack_ms=200,
                       fade_level=0, fade_ms=200, duration_ms=1000)
        r = ForceModel.evaluate(s, 0.0, Kinematics())
        self.assertAlmostEqual(r.fy, 0.0, places=6)
        r = ForceModel.evaluate(s, 0.1, Kinematics())
        self.assertAlmostEqual(r.magnitude, 2000.0, places=4)
        r = ForceModel.evaluate(s, 0.9, Kinematics())
        self.assertAlmostEqual(r.magnitude, 2000.0, places=4)

    def test_condition_spring(self):
        s = EffectSpec(effect=FfbEffect.SPRING, positive_coefficient=6000, negative_coefficient=6000)
        r = ForceModel.evaluate(s, 0, Kinematics(roll_pos=0.5))
        self.assertAlmostEqual(r.fx, -3000.0, places=6)
        r = ForceModel.evaluate(s, 0, Kinematics(roll_pos=-0.5))
        self.assertAlmostEqual(r.fx, 3000.0, places=6)
        db = EffectSpec(effect=FfbEffect.SPRING, dead_band=1000)
        r = ForceModel.evaluate(db, 0, Kinematics(roll_pos=0.05))
        self.assertAlmostEqual(r.fx, 0.0, places=9)

    def test_combined(self):
        spring = EffectSpec(effect=FfbEffect.SPRING, positive_coefficient=5000)
        main = EffectSpec(effect=FfbEffect.CONSTANT_FORCE, direction_deg=0, magnitude=3000)
        r = ForceModel.evaluate_combined(spring, main, 0, Kinematics(roll_pos=0.5))
        self.assertAlmostEqual(r.fx, -2500.0, places=6)
        self.assertAlmostEqual(r.fy, 3000.0, places=6)

    def test_result_direction(self):
        self.assertAlmostEqual(ForceModel.Result(3000, 0, 0).direction_deg, 90.0, places=6)
        self.assertAlmostEqual(ForceModel.Result(0, 3000, 0).direction_deg, 180.0, places=6)
        self.assertAlmostEqual(ForceModel.Result(0, -3000, 0).direction_deg, 0.0, places=6)

    def test_sawtooth(self):
        s = self._spec(effect=FfbEffect.SAWTOOTH_UP, period_ms=1000)
        self.assertAlmostEqual(ForceModel.evaluate(s, 0.0, Kinematics()).instantaneous, -1.0, places=9)
        self.assertAlmostEqual(ForceModel.evaluate(s, 0.5, Kinematics()).instantaneous, 0.0, places=9)
        s = self._spec(effect=FfbEffect.SAWTOOTH_DOWN, period_ms=1000)
        self.assertAlmostEqual(ForceModel.evaluate(s, 0.0, Kinematics()).instantaneous, 1.0, places=9)
        self.assertAlmostEqual(ForceModel.evaluate(s, 0.5, Kinematics()).instantaneous, 0.0, places=9)

    def test_phase_wrap(self):
        s = self._spec(effect=FfbEffect.SINE, period_ms=1000, phase_deg=360)
        r = ForceModel.evaluate(s, 0.0, Kinematics())
        self.assertAlmostEqual(r.instantaneous, 0.0, places=9)

    def test_ramp_infinite_holds_end(self):
        s = EffectSpec(effect=FfbEffect.RAMP_FORCE, ramp_start=0, ramp_end=8000, duration_ms=0)
        r = ForceModel.evaluate(s, 10.0, Kinematics())
        self.assertAlmostEqual(r.instantaneous, 1.0, places=9)
        self.assertAlmostEqual(r.magnitude, 8000.0, places=6)

    def test_condition_saturation_and_friction(self):
        s = EffectSpec(effect=FfbEffect.SPRING, positive_coefficient=6000,
                       positive_saturation=1000)
        r = ForceModel.evaluate(s, 0, Kinematics(roll_pos=1.0))
        self.assertAlmostEqual(r.fx, -1000.0, places=6)
        f = EffectSpec(effect=FfbEffect.FRICTION)
        r = ForceModel.evaluate(f, 0, Kinematics(roll_vel=0.5))
        self.assertAlmostEqual(r.fx, -6000.0, places=6)
        r = ForceModel.evaluate(f, 0, Kinematics(roll_vel=0.0))
        self.assertAlmostEqual(r.fx, 0.0, places=9)
        d = EffectSpec(effect=FfbEffect.DAMPER, positive_coefficient=3000)
        r = ForceModel.evaluate(d, 0, Kinematics(roll_vel=2.0))
        self.assertAlmostEqual(r.fx, -3000.0, places=6)

    def test_words(self):
        self.assertEqual(DirWord(0), "pull / nose-up")
        self.assertEqual(DirWord(90), "roll left")
        self.assertEqual(DirWord(270), "roll right")
        self.assertEqual(Pretty(FfbEffect.CONSTANT_FORCE), "Constant force")


if __name__ == "__main__":
    unittest.main()
