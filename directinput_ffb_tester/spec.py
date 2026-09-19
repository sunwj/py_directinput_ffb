"""Effect specification and pure force-prediction model for the test tool.

This is a literal port of FFBTestTool's EffectSpec/ForceModel. All numeric
conventions (DirectInput direction = where the force comes from; felt force is
its negation) are preserved so the tool never "invents" force it does not send.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class FfbEffect(str, Enum):
    CONSTANT_FORCE = "ConstantForce"
    RAMP_FORCE = "RampForce"
    SQUARE = "Square"
    SINE = "Sine"
    TRIANGLE = "Triangle"
    SAWTOOTH_UP = "SawtoothUp"
    SAWTOOTH_DOWN = "SawtoothDown"
    SPRING = "Spring"
    DAMPER = "Damper"
    INERTIA = "Inertia"
    FRICTION = "Friction"


PRETTY = {
    FfbEffect.CONSTANT_FORCE: "Constant force",
    FfbEffect.RAMP_FORCE: "Ramp force",
    FfbEffect.SAWTOOTH_UP: "Sawtooth up",
    FfbEffect.SAWTOOTH_DOWN: "Sawtooth down",
}


def Pretty(effect: FfbEffect) -> str:
    return PRETTY.get(effect, effect.value)


def DirWord(deg: float) -> str:
    d = ((deg % 360) + 360) % 360
    if d < 22.5 or d >= 337.5:
        return "pull / nose-up"
    if d < 67.5:
        return "pull-left"
    if d < 112.5:
        return "roll left"
    if d < 157.5:
        return "push-left"
    if d < 202.5:
        return "push / nose-down"
    if d < 247.5:
        return "push-right"
    if d < 292.5:
        return "roll right"
    return "pull-right"


def direction_components(angle_deg: float) -> tuple[float, float]:
    """Cartesian components of the DI direction: (sin, -cos) in -1..1."""
    rad = math.radians(angle_deg)
    return math.sin(rad), -math.cos(rad)


@dataclass
class EffectSpec:
    effect: FfbEffect = FfbEffect.CONSTANT_FORCE
    direction_deg: int = 0
    magnitude: int = 4000
    duration_ms: int = 0
    period_ms: int = 1500
    phase_deg: int = 0
    periodic_offset: int = 0
    ramp_start: int = 0
    ramp_end: int = 8000
    positive_coefficient: int = 6000
    negative_coefficient: int = 6000
    positive_saturation: int = 10000
    negative_saturation: int = 10000
    dead_band: int = 0
    center_offset_x: int = 0
    center_offset_y: int = 0
    apply_roll: bool = True
    apply_pitch: bool = True
    use_envelope: bool = False
    attack_level: int = 0
    attack_ms: int = 200
    fade_level: int = 0
    fade_ms: int = 200

    @property
    def is_condition(self) -> bool:
        return self.effect in (FfbEffect.SPRING, FfbEffect.DAMPER,
                               FfbEffect.INERTIA, FfbEffect.FRICTION)

    @property
    def is_periodic(self) -> bool:
        return self.effect in (FfbEffect.SQUARE, FfbEffect.SINE,
                               FfbEffect.TRIANGLE, FfbEffect.SAWTOOTH_UP,
                               FfbEffect.SAWTOOTH_DOWN)

    @property
    def is_ramp(self) -> bool:
        return self.effect == FfbEffect.RAMP_FORCE

    def clone(self) -> "EffectSpec":
        return EffectSpec(**self.__dict__)


@dataclass
class Kinematics:
    roll_pos: float = 0.0
    pitch_pos: float = 0.0
    roll_vel: float = 0.0
    pitch_vel: float = 0.0
    roll_acc: float = 0.0
    pitch_acc: float = 0.0


class ForceModel:
    """Predicts the commanded force for visualisation; mirrors a conformant PID device."""

    @dataclass
    class Result:
        fx: float
        fy: float
        instantaneous: float

        @property
        def magnitude(self) -> float:
            return math.hypot(self.fx, self.fy)

        @property
        def direction_deg(self) -> float:
            if self.magnitude < 1:
                return float("nan")
            d = math.degrees(math.atan2(self.fx, -self.fy))
            return d + 360 if d < 0 else d

    @staticmethod
    def evaluate_combined(spring: Optional[EffectSpec], main: Optional[EffectSpec],
                          t_seconds: float, k: Kinematics) -> "ForceModel.Result":
        fx = fy = 0.0
        wave = 0.0
        if spring is not None:
            r = ForceModel.evaluate(spring, t_seconds, k)
            fx += r.fx
            fy += r.fy
        if main is not None:
            r = ForceModel.evaluate(main, t_seconds, k)
            fx += r.fx
            fy += r.fy
            wave = r.instantaneous
        return ForceModel.Result(fx, fy, wave)

    @staticmethod
    def evaluate(s: EffectSpec, t_seconds: float, k: Kinematics) -> "ForceModel.Result":
        if s.is_condition:
            fx = (ForceModel._condition(s, k.roll_pos, k.roll_vel, k.roll_acc, s.center_offset_x)
                  if s.apply_roll else 0.0)
            fy = (ForceModel._condition(s, k.pitch_pos, k.pitch_vel, k.pitch_acc, s.center_offset_y)
                  if s.apply_pitch else 0.0)
            return ForceModel.Result(fx, fy, 0.0)

        rad = math.radians(s.direction_deg)
        ux = -math.sin(rad)
        uy = math.cos(rad)

        if s.effect == FfbEffect.CONSTANT_FORCE:
            wave = 1.0
            value = float(s.magnitude)
        elif s.effect == FfbEffect.RAMP_FORCE:
            wave = ForceModel._ramp_frac(s, t_seconds)
            value = s.ramp_start + (s.ramp_end - s.ramp_start) * wave
        else:
            value, wave = ForceModel._periodic(s, t_seconds)

        value *= ForceModel._envelope(s, t_seconds)
        return ForceModel.Result(value * ux, value * uy, wave)

    @staticmethod
    def _periodic(s: EffectSpec, t: float) -> tuple[float, float]:
        period_sec = max(1, s.period_ms) / 1000.0
        u = (t / period_sec) + s.phase_deg / 360.0
        u -= math.floor(u)
        if s.effect == FfbEffect.SINE:
            w = math.sin(2 * math.pi * u)
        elif s.effect == FfbEffect.SQUARE:
            w = 1.0 if u < 0.5 else -1.0
        elif s.effect == FfbEffect.TRIANGLE:
            w = (4 * u - 1) if u < 0.5 else (3 - 4 * u)
        elif s.effect == FfbEffect.SAWTOOTH_UP:
            w = 2 * u - 1
        else:
            w = 1 - 2 * u
        return s.periodic_offset + s.magnitude * w, w

    @staticmethod
    def _ramp_frac(s: EffectSpec, t: float) -> float:
        if s.duration_ms <= 0:
            return 1.0
        return max(0.0, min(1.0, t / (s.duration_ms / 1000.0)))

    @staticmethod
    def _envelope(s: EffectSpec, t: float) -> float:
        if not s.use_envelope:
            return 1.0
        mag = max(1, abs(s.magnitude))
        atk = s.attack_ms / 1000.0
        fade = s.fade_ms / 1000.0
        dur = s.duration_ms / 1000.0 if s.duration_ms > 0 else float("inf")
        if atk > 0 and t < atk:
            return (s.attack_level + (mag - s.attack_level) * (t / atk)) / mag
        if fade > 0 and t > dur - fade:
            return (s.fade_level + (mag - s.fade_level) * ((dur - t) / fade)) / mag
        return 1.0

    @staticmethod
    def _condition(s: EffectSpec, pos: float, vel: float, acc: float, center_raw: int) -> float:
        if s.effect == FfbEffect.SPRING:
            metric = pos
        elif s.effect == FfbEffect.DAMPER:
            metric = max(-1.0, min(1.0, vel))
        elif s.effect == FfbEffect.INERTIA:
            metric = max(-1.0, min(1.0, acc))
        else:
            metric = math.copysign(1.0, vel) if abs(vel) > 0.02 else 0.0
        center = center_raw / 10000.0
        db = s.dead_band / 10000.0
        d = metric - center
        if d > db:
            f = -s.positive_coefficient * (d - db)
            sat = s.positive_saturation
        elif d < -db:
            f = -s.negative_coefficient * (d + db)
            sat = s.negative_saturation
        else:
            return 0.0
        return max(-sat, min(sat, f))


__all__ = ["FfbEffect", "Pretty", "DirWord", "direction_components",
           "EffectSpec", "Kinematics", "ForceModel"]
