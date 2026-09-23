# FFB Test Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port barsk/FFBTestTool to a new PyQt6 GUI tester (`directinput_ffb_tester` package) on top of the existing `directinput_ffb` library, with the library extended by new additive APIs.

**Architecture:** Library additions first (constants, device helpers, live `EffectHandle.apply` + envelope), then a package of pure-logic modules (spec/ForceModel, log), then the device session, then the Qt views and main window, then a root launcher. The existing `py_directinput_ffb_gui_tester.py` is untouched.

**Tech Stack:** Python 3 (ctypes/comtypes binding), PyQt6 (GUI), unittest (built-in test runner — no new deps).

**Spec:** `docs/superpowers/specs/2026-09-19-ffb-test-tool-design.md`

## Global Constraints

- Windows only; import name `directinput_ffb`; run scripts from repo root.
- All library additions are additive/backward-compatible; do not modify existing signatures or behavior.
- Direction convention: DirectInput "comes-from"; sent as Cartesian `(sin, -cos)`; felt force `(-sin, +cos)`.
- Effect gain fixed 10000; strength via Magnitude; device gain separate (DIPROP_FFGAIN).
- Condition effects: no envelope, per-axis DICONDITION, direction polar `{0,0}` (library default).
- Never let a library call raise into the Qt timer — `DeviceSession` wraps all calls, records `last_error`, logs.
- Tests: `python -m unittest discover -s tests -v` from repo root (no pytest dependency).
- No commits to git unless the user later asks (repo policy).

## File Structure

```
directinput_ffb/dinput_definitions.py    MODIFY  +DIPROPDWORD, +DIPROP_FFGAIN/AUTOCENTER, +SFFC_STOPALL, +DIEP_STARTDELAY
directinput_ffb/dinput_api.py            MODIFY  +get_device_gain/set_device_gain/set_autocenter/stop_all_effects
directinput_ffb/dinput_effects.py        MODIFY  +EffectHandle.apply/_set_direction, +envelope kwargs on 3 factories
directinput_ffb/__init__.py              MODIFY  +exports
directinput_ffb_tester/spec.py           CREATE  FfbEffect, EffectSpec, ForceModel, Pretty/DirWord
directinput_ffb_tester/log.py            CREATE  Log (file append + OpenInEditor)
directinput_ffb_tester/device.py         CREATE  PollResult, DeviceSession (2 slots)
directinput_ffb_tester/views.py          CREATE  YokeView, SliderRow, DirPad, CollapsibleGroup
directinput_ffb_tester/window.py         CREATE  MainWindow (layout, timer, wiring, debug)
directinput_ffb_tester/__main__.py       CREATE  app entry
directinput_ffb_test_tool.py             CREATE  root launcher
tests/test_definitions.py                CREATE
tests/test_spec.py                       CREATE
tests/test_log.py                        CREATE
tests/test_views.py                      CREATE
tests/test_device.py                     CREATE
README.md / AGENTS.md                    MODIFY
```

---

### Task 1: Library constants and DIPROPDWORD

**Files:**
- Modify: `directinput_ffb/dinput_definitions.py` (constants block + struct block)
- Test: `tests/test_definitions.py` (create)

**Interfaces:**
- Produces: `DIPROPDWORD` (ctypes struct, 20 bytes on x64), `DIPROP_FFGAIN = MAKEDIPROP(7)`, `DIPROP_AUTOCENTER = MAKEDIPROP(9)`, `DIPROPAUTOCENTER_OFF = 0`, `SFFC_STOPALL = 0x00000020`, `DIEP_STARTDELAY = 0x00000200` (and `DIEP_ALLPARAMS` re-expressed with it).

- [ ] **Step 1: Create the failing test**

`tests/test_definitions.py`:
```python
import ctypes as C
import unittest
from directinput_ffb.dinput_definitions import (
    DIPROPDWORD, DIPROP_FFGAIN, DIPROP_AUTOCENTER, DIPROPAUTOCENTER_OFF,
    SFFC_STOPALL, DIEP_STARTDELAY, DIEP_ALLPARAMS,
)


class TestDefinitions(unittest.TestCase):
    def test_dipropdword_size(self):
        self.assertEqual(C.sizeof(DIPROPDWORD), 20)

    def test_prop_ids(self):
        self.assertEqual(int(DIPROP_FFGAIN.value), 7)
        self.assertEqual(int(DIPROP_AUTOCENTER.value), 9)
        self.assertEqual(DIPROPAUTOCENTER_OFF, 0)

    def test_ffb_constants(self):
        self.assertEqual(SFFC_STOPALL, 0x00000020)
        self.assertEqual(DIEP_STARTDELAY, 0x00000200)
        self.assertEqual(DIEP_ALLPARAMS, 0x000003FF)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run and verify it fails**

Run: `python -m unittest tests.test_definitions -v`
Expected: FAIL �� `ImportError: cannot import name 'DIPROPDWORD'`

- [ ] **Step 3: Implement**

In `dinput_definitions.py`, after the `DIEP_TYPESPECIFICPARAMS` constant (line ~89) add:
```python
DIEP_STARTDELAY = 0x00000200
```
and replace the inlined `| 0x00000200  # DIEP_STARTDELAY` in `DIEP_ALLPARAMS` with `| DIEP_STARTDELAY`.

In the flags block add:
```python
DIPROP_FFGAIN = MAKEDIPROP(7)
DIPROP_AUTOCENTER = MAKEDIPROP(9)
DIPROPAUTOCENTER_OFF = 0
SFFC_STOPALL = 0x00000020
```

After `DIPROPRANGE` (line ~450) add:
```python
class DIPROPDWORD(C.Structure):
    _fields_ = [
        ("diph", DIPROPHEADER),
        ("dwData", DWORD),
    ]
```

- [ ] **Step 4: Run and verify it passes**

Run: `python -m unittest tests.test_definitions -v`
Expected: 3 tests PASS.

---

### Task 2: Device helper functions (gain / autocenter / stop-all)

**Files:**
- Modify: `directinput_ffb/dinput_api.py` (properties section)
- Modify: `directinput_ffb/__init__.py` (exports)
- Test: `tests/test_definitions.py` (append)

**Interfaces:**
- Consumes: `DIPROP_FFGAIN`, `DIPROP_AUTOCENTER`, `DIPROPAUTOCENTER_OFF`, `SFFC_STOPALL`, `DIPROPDWORD` (Task 1).
- Produces: `get_device_gain(device) -> int`, `set_device_gain(device, gain) -> None`, `set_autocenter(device, on: bool) -> None`, `stop_all_effects(device) -> None`.

- [ ] **Step 1: Append failing test**

In `tests/test_definitions.py`:
```python
import directinput_ffb


class TestDeviceHelpers(unittest.TestCase):
    def test_exports(self):
        self.assertTrue(callable(directinput_ffb.get_device_gain))
        self.assertTrue(callable(directinput_ffb.set_device_gain))
        self.assertTrue(callable(directinput_ffb.set_autocenter))
        self.assertTrue(callable(directinput_ffb.stop_all_effects))
```

- [ ] **Step 2: Run and verify it fails**

Run: `python -m unittest tests.test_definitions -v`
Expected: FAIL �� AttributeError.

- [ ] **Step 3: Implement**

In `dinput_api.py` imports add `DIPROP_FFGAIN`, `DIPROP_AUTOCENTER`, `DIPROPAUTOCENTER_OFF`, `SFFC_STOPALL`, `DIPROPDWORD`.
Append to the properties section:
```python
def get_device_gain(device: POINTER(IDirectInputDevice8W)) -> int:
    prop = DIPROPDWORD()
    prop.diph.dwSize = C.sizeof(DIPROPDWORD)
    prop.diph.dwHeaderSize = C.sizeof(DIPROPHEADER)
    prop.diph.dwObj = 0
    prop.diph.dwHow = DIPH_DEVICE
    device.GetProperty(DIPROP_FFGAIN, C.byref(prop))
    return int(prop.dwData)


def set_device_gain(device: POINTER(IDirectInputDevice8W), gain: int) -> None:
    prop = DIPROPDWORD()
    prop.diph.dwSize = C.sizeof(DIPROPDWORD)
    prop.diph.dwHeaderSize = C.sizeof(DIPROPHEADER)
    prop.diph.dwObj = 0
    prop.diph.dwHow = DIPH_DEVICE
    prop.dwData = gain
    check_hr(device.SetProperty(DIPROP_FFGAIN, C.byref(prop)), "SetProperty(DIPROP_FFGAIN)")


def set_autocenter(device: POINTER(IDirectInputDevice8W), on: bool) -> None:
    prop = DIPROPDWORD()
    prop.diph.dwSize = C.sizeof(DIPROPDWORD)
    prop.diph.dwHeaderSize = C.sizeof(DIPROPHEADER)
    prop.diph.dwObj = 0
    prop.diph.dwHow = DIPH_DEVICE
    prop.dwData = 1 if on else DIPROPAUTOCENTER_OFF
    check_hr(device.SetProperty(DIPROP_AUTOCENTER, C.byref(prop)), "SetProperty(DIPROP_AUTOCENTER)")


def stop_all_effects(device: POINTER(IDirectInputDevice8W)) -> None:
    check_hr(device.SendForceFeedbackCommand(SFFC_STOPALL), "SendForceFeedbackCommand(SFFC_STOPALL)")
```
In `directinput_ffb/__init__.py` import/export the four functions.

- [ ] **Step 4: Run and verify it passes**

Run: `python -m unittest tests.test_definitions -v`
Expected: ALL PASS. (Real behavior is hardware-gated; noted in Task 8 verification.)

---

### Task 3: EffectHandle.apply, _set_direction, envelope support

**Files:**
- Modify: `directinput_ffb/dinput_effects.py` (EffectHandle, _build_effect_description, _create_effect, 3 factories)

**Interfaces:**
- Consumes: `DIEP_STARTDELAY` (Task 1); existing `DIEP_DURATION/DIEP_DIRECTION/DIEP_GAIN/DIEP_TYPESPECIFICPARAMS/DIEP_TRIGGERBUTTON/DIEP_ENVELOPE/DIEP_START`, `DIENVELOPE`, `angle_deg_to_cartesian`, `DIEFF_CARTESIAN`.
- Produces:
  - `EffectHandle` new fields `direction_basis: int = 0`, `direction_hundredths_deg: int = 0` (defaults keep old construction working).
  - `EffectHandle.apply(*, duration_ms=None, direction_hundredths_deg=None, gain=None, envelope=None, type_specific=None, start=False) -> None`
  - `EffectHandle._set_direction(hundredths: int) -> None` (rewrites kept-alive array in place).
  - `create_constant_force_effect`, `create_ramp_force_effect`, `create_periodic_effect` gain `attack_level=None, attack_time_ms=None, fade_level=None, fade_time_ms=None` (all must be set together to enable), which build a `DIENVELOPE`.
  - Envelope instance is attached to `EffectHandle.keepalive` by `_create_effect`.

- [ ] **Step 1: Failing tests**

`tests/test_effects_directions.py` (create):
```python
import unittest
from directinput_ffb.dinput_definitions import DIEFFECT, DICONSTANTFORCE, DIEFF_CARTESIAN, DIEFF_POLAR
from directinput_ffb.dinput_effects import EffectHandle, _build_effect_description
import ctypes as C


class TestDirectionRewrite(unittest.TestCase):
    def _handle(self, axes_offsets, basis):
        n = len(axes_offsets)
        axes = (C.c_uint * n)(*axes_offsets)
        directions = (C.c_long * n)(0) if n == 1 else (C.c_long * n)(0, 0)
        h = EffectHandle(
            effect=None, dieffect=DIEFFECT(), axes=axes, directions=directions,
            type_specific=DICONSTANTFORCE(), direction_basis=basis,
        )
        return h

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


class TestEnvelopeBuild(unittest.TestCase):
    def test_envelope_wired(self):
        from directinput_ffb.dinput_definitions import DIENVELOPE
        env = DIENVELOPE()
        env.dwSize = C.sizeof(DIENVELOPE)
        env.dwAttackLevel = 0
        env.dwAttackTime = 200 * 1000
        env.dwFadeLevel = 0
        env.dwFadeTime = 200 * 1000
        desc, axes, directions = _build_effect_description(
            axes_offsets=(0, 4), direction_hundredths_deg=0, direction_basis=DIEFF_CARTESIAN,
            duration_us=1_000_000, type_specific=DICONSTANTFORCE(), envelope=env,
        )
        self.assertIsNotNone(desc.lpEnvelope)
        self.assertEqual(desc.lpEnvelope.contents.dwAttackTime, 200000)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run and verify it fails**

Run: `python -m unittest tests.test_effects_directions -v`
Expected: FAIL (AttributeError `_set_direction`, TypeError envelope kw, etc.)

- [ ] **Step 3: Implement**

First extend the imports in `dinput_effects.py` from `dinput_definitions`: add
`DIENVELOPE`, `DIEP_DURATION`, `DIEP_DIRECTION`, `DIEP_GAIN`, `DIEP_ENVELOPE`,
`DIEP_TRIGGERBUTTON`, `DIEP_STARTDELAY` (keep the already-imported
`DIEP_TYPESPECIFICPARAMS`, `DIEP_START`).

`EffectHandle` dataclass: add fields after `keepalive`:
```python
    direction_basis: int = 0
    direction_hundredths_deg: int = 0
```
Add methods:
```python
    def _set_direction(self, direction_hundredths_deg: int) -> None:
        self.direction_hundredths_deg = direction_hundredths_deg
        if len(self.directions) == 1:
            self.directions[0] = 0
        elif self.direction_basis == DIEFF_CARTESIAN:
            cx, cy = angle_deg_to_cartesian(direction_hundredths_deg / 100)
            self.directions[0] = cx
            self.directions[1] = cy
        else:
            self.directions[0] = direction_hundredths_deg
            self.directions[1] = 0

    def apply(self, *, duration_ms=None, direction_hundredths_deg=None,
              gain=None, envelope=None, type_specific=None, start=False) -> None:
        flags = (DIEP_DURATION | DIEP_DIRECTION | DIEP_GAIN | DIEP_TYPESPECIFICPARAMS
                 | DIEP_STARTDELAY | DIEP_TRIGGERBUTTON)
        self.dieffect.lpEnvelope = None
        if envelope is not None:
            self.dieffect.lpEnvelope = C.cast(C.pointer(envelope), POINTER(DIENVELOPE))
            self.keepalive = self.keepalive + (envelope,)
            flags |= DIEP_ENVELOPE
        if duration_ms is not None:
            self.dieffect.dwDuration = 0xFFFFFFFF if duration_ms <= 0 else duration_ms * 1000
        if gain is not None:
            self.dieffect.dwGain = gain
        if direction_hundredths_deg is not None:
            self._set_direction(direction_hundredths_deg)
        if type_specific is not None:
            self.type_specific = type_specific
            self.dieffect.cbTypeSpecificParams = C.sizeof(type_specific)
            self.dieffect.lpvTypeSpecificParams = C.cast(C.pointer(type_specific), LPVOID)
        if start:
            flags |= DIEP_START
        hr = self.effect.SetParameters(C.byref(self.dieffect), flags)
        check_hr(hr, "IDirectInputEffect.SetParameters")
```

`_build_effect_description`: add keyword `envelope=None`; at the end:
```python
    if envelope is not None:
        effect_desc.lpEnvelope = C.cast(C.pointer(envelope), POINTER(DIENVELOPE))
    return effect_desc, axes, directions
```
(also keep the plain `None` assignment for the no-envelope path).

`_create_effect`: add `envelope: object | None = None` param; build `keepalive = keepalive + ((envelope,) if envelope is not None else ())`; pass `direction_basis=...`, `direction_hundredths_deg=...` into `handle_cls(...)` (add the two constructor args; keep positional order after `keepalive`).

The three factories: add kwargs
`attack_level=None, attack_time_ms=None, fade_level=None, fade_time_ms=None`
and before `_build_effect_description`:
```python
    envelope = None
    if attack_level is not None:
        env = DIENVELOPE()
        env.dwSize = C.sizeof(DIENVELOPE)
        env.dwAttackLevel = attack_level
        env.dwAttackTime = (attack_time_ms or 0) * 1000
        env.dwFadeLevel = fade_level
        env.dwFadeTime = (fade_time_ms or 0) * 1000
        envelope = env
```
pass `envelope=envelope` to `_build_effect_description` and `envelope=envelope` (if not None) to `_create_effect`.

**Do not** change `create_condition_effect`/`_build_condition_description` (no envelope for conditions).

- [ ] **Step 4: Run and verify it passes**

Run: `python -m unittest tests.test_effects_directions -v`
Expected: 4 tests PASS.

---

### Task 4: spec.py �� EffectSpec + ForceModel

**Files:**
- Create: `directinput_ffb_tester/spec.py`, `tests/test_spec.py`

**Interfaces:**
- Produces: `FfbEffect` (str enum), `EffectSpec` dataclass (field names mirror the C# `EffectSpec`), `Direction.direction_components(deg) -> (cx, cy)` = `(sin, -cos)`, `ForceModel.Result(fx, fy, instantaneous)` with `.magnitude` and `.direction_deg` properties, `ForceModel.Kinematics`, `ForceModel.evaluate(spec, t_seconds, kinematics)`, `ForceModel.evaluate_combined(spring, main, t, k)`, `Pretty(effect)`, `DirWord(deg)`.

- [ ] **Step 1: Create `directinput_ffb_tester/spec.py`**

````python
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
````

- [ ] **Step 2: Create `tests/test_spec.py`**

````python
import math
import unittest
from directinput_ffb_tester.spec import (
    FfbEffect, EffectSpec, ForceModel, Kinematics, direction_components, DirWord, Pretty,
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
        self.assertAlmostEqual(r.fx, -4000.0)   # felt force negates the DI direction
        self.assertAlmostEqual(r.fy, 0.0, places=6)
        self.assertAlmostEqual(r.direction_deg, 270.0)

    def test_sine_quarter(self):
        s = self._spec(effect=FfbEffect.SINE, period_ms=1500, direction_deg=0)
        r = ForceModel.evaluate(s, 0.375, Kinematics())   # quarter period
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
        main = self._spec(effect=FfbEffect.CONSTANT_FORCE, direction_deg=0, magnitude=3000)
        r = ForceModel.evaluate_combined(spring, main, 0, Kinematics(roll_pos=0.5))
        self.assertAlmostEqual(r.fx, -2500.0, places=6)
        self.assertAlmostEqual(r.fy, 3000.0, places=6)

    def test_result_direction(self):
        self.assertAlmostEqual(ForceModel.Result(3000, 0, 0).direction_deg, 90.0, places=6)
        self.assertAlmostEqual(ForceModel.Result(0, 3000, 0).direction_deg, 180.0, places=6)
        self.assertAlmostEqual(ForceModel.Result(0, -3000, 0).direction_deg, 0.0, places=6)

    def test_words(self):
        self.assertEqual(DirWord(0), "pull / nose-up")
        self.assertEqual(DirWord(90), "roll left")
        self.assertEqual(DirWord(270), "roll right")
        self.assertEqual(Pretty(FfbEffect.CONSTANT_FORCE), "Constant force")


if __name__ == "__main__":
    unittest.main()
````

- [ ] **Step 3: Run and verify it passes**

Run: `python -m unittest tests.test_spec -v`
Expected: 9 tests PASS (pure Python; needs `directinput_ffb_tester/spec.py` only, no Qt).

---

### Task 5: log.py

**Files:**
- Create: `directinput_ffb_tester/log.py`, `tests/test_log.py`

**Interfaces:**
- Produces: `Log.set_dir(path)` (test hook; default `%LOCALAPPDATA%\py_directinput_ffb`), `Log.FilePath` (module attr, str), `Log.info(msg)`, `Log.warn(msg)`, `Log.error(msg, exc=None)`, `Log.open_in_editor()`.

- [ ] **Step 1: Create `directinput_ffb_tester/log.py`**

````python
"""Session log for the test tool: appended timestamped lines plus stack traces."""
from __future__ import annotations

import datetime
import inspect
import os
import threading
import traceback

_log_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                        "py_directinput_ffb")
FilePath = os.path.join(_log_dir, "test_tool.log")
_lock = threading.Lock()


def set_dir(path: str) -> None:
    global _log_dir, FilePath
    _log_dir = path
    FilePath = os.path.join(_log_dir, "test_tool.log")


def _write(kind: str, msg: str, exc: object = None) -> None:
    globals()  # keep module attrs alive
    line = (f"{datetime.datetime.now().isoformat(timespec='milliseconds')} "
            f"[{kind}] {msg}")
    caller = inspect.currentframe().f_back
    if caller is not None and caller.f_back is not None:
        line += f"  ({caller.f_back.f_code.co_name})"
    if exc is not None:
        line += "\n" + "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    with _lock:
        try:
            os.makedirs(_log_dir, exist_ok=True)
            with open(FilePath, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except OSError:
            pass


def info(msg: str) -> None:
    _write("INFO", msg)


def warn(msg: str) -> None:
    _write("WARN", msg)


def error(msg: str, exc: object = None) -> None:
    _write("ERROR", msg, exc)


def open_in_editor() -> None:
    try:
        os.startfile(FilePath)
    except Exception:
        pass


__all__ = ["FilePath", "set_dir", "info", "warn", "error", "open_in_editor"]
````

- [ ] **Step 2: Create `tests/test_log.py`**

````python
import os
import tempfile
import unittest
from directinput_ffb_tester import log


class TestLog(unittest.TestCase):
    def test_append(self):
        with tempfile.TemporaryDirectory() as d:
            log.set_dir(d)
            log.info("hello")
            log.warn("world")
            with open(log.FilePath, encoding="utf-8") as fh:
                text = fh.read()
            self.assertIn("[INFO] hello", text)
            self.assertIn("[WARN] world", text)


if __name__ == "__main__":
    unittest.main()
````
(Each test run appends to the same tmp dir twice �� acceptable; assertions are substring-based.)

- [ ] **Step 3: Run and verify it passes**

Run: `python -m unittest tests.test_log -v`
Expected: 1 test PASS.

---

### Task 6: device.py �� DeviceSession

**Files:**
- Create: `directinput_ffb_tester/device.py`, `tests/test_device.py`

**Interfaces:**
- Consumes: Tasks 1-4 (library helpers, spec).
- Produces:
  - `PollResult(ok: bool, raw_roll: int, raw_pitch: int, roll: float, pitch: float, buttons: int)`.
  - `DeviceSession` �� `enumerate() -> list[EnumeratedDevice]`; `connect(guid_instance, hwnd) -> bool`;
    `disconnect() -> None`; `poll() -> PollResult`; `apply_main(spec) -> None`; `start_main()`;
    `stop_main()`; `apply_spring(spec)`; `start_spring()`; `stop_spring()`; `stop_all()`;
    `set_device_gain(gain)`; `get_device_gain() -> int`; `roll_actuator`/`pitch_actuator`/
    `ffb_axes`/`device_name`/`connected`/`main_running`/`spring_running`/`last_error`.
  - Pure helper `select_condition_axes(apply_roll, apply_pitch, roll_actuator, pitch_actuator, ffb_axes) -> list[int]`.
  - `AxisSelection` handling: `effects_axes(spec, ffb_axes, roll_actuator, pitch_actuator) -> (axis_offsets, dirs)`.

- [ ] **Step 1: Create `directinput_ffb_tester/device.py`**

````python
"""Device session: connect, poll, and two effect slots (background spring + main)."""
from __future__ import annotations

from dataclasses import dataclass

from directinput_ffb import (
    create_direct_input, enum_devices, create_device, set_cooperative_level,
    set_data_format, acquire, unacquire,
    enum_ffb_axes_actuator_offsets, set_axis_range, get_device_gain, set_device_gain,
    set_autocenter, stop_all_effects,
    create_constant_force_effect, create_ramp_force_effect, create_square_effect,
    create_sine_effect, create_triangle_effect, create_sawtooth_up_effect,
    create_sawtooth_down_effect, create_spring_effect, create_damper_effect,
    create_inertia_effect, create_friction_effect,
)
from directinput_ffb.dinput_api import build_joystick_data_format
from directinput_ffb.dinput_definitions import (
    DIJOFS_X, DIJOFS_Y, DIEFF_CARTESIAN, DIEFF_POLAR, C, DIJOYSTATE,
)
from directinput_ffb.dinput_effects import EffectHandle

from . import log
from .spec import FfbEffect, EffectSpec, direction_components

AXIS_RANGE = 10000

EFFECT_GUID_FACTORY = {
    FfbEffect.CONSTANT_FORCE: create_constant_force_effect,
    FfbEffect.RAMP_FORCE: create_ramp_force_effect,
    FfbEffect.SQUARE: create_square_effect,
    FfbEffect.SINE: create_sine_effect,
    FfbEffect.TRIANGLE: create_triangle_effect,
    FfbEffect.SAWTOOTH_UP: create_sawtooth_up_effect,
    FfbEffect.SAWTOOTH_DOWN: create_sawtooth_down_effect,
    FfbEffect.SPRING: create_spring_effect,
    FfbEffect.DAMPER: create_damper_effect,
    FfbEffect.INERTIA: create_inertia_effect,
    FfbEffect.FRICTION: create_friction_effect,
}


def select_condition_axes(apply_roll, apply_pitch, roll_actuator, pitch_actuator, ffb_axes):
    axes = []
    if apply_roll and roll_actuator:
        axes.append(DIJOFS_X)
    if apply_pitch and pitch_actuator:
        axes.append(DIJOFS_Y)
    if not axes and ffb_axes:
        axes = [ffb_axes[0]]
    return axes


@dataclass
class PollResult:
    ok: bool
    raw_roll: int
    raw_pitch: int
    roll: float
    pitch: float
    buttons: int = 0


class _Slot:
    def __init__(self, name: str, device: "DeviceSession") -> None:
        self.name = name
        self.device = device
        self.fx: EffectHandle | None = None
        self.running = False
        self.last_type: FfbEffect | None = None
        self.last_axes: tuple[int, ...] = ()

    def dispose(self) -> None:
        if self.fx is not None:
            try:
                self.fx.unload()
            except Exception as exc:
                log.warn(f"[{self.name}] unload failed: {exc}")
            self.fx = None
            self.last_type = None
            self.last_axes = ()
            self.running = False


class DeviceSession:
    def __init__(self) -> None:
        self._di = None
        self._device = None
        self._hwnd = None
        self._data_format = None
        self.ffb_axes: list[int] = [DIJOFS_X, DIJOFS_Y]
        self._main = _Slot("main", self)
        self._spring = _Slot("spring", self)
        self.device_name = "(not connected)"
        self.last_error = ""
        self.gain = 10000

    @property
    def connected(self) -> bool:
        return self._device is not None

    @property
    def main_running(self) -> bool:
        return self._main.running

    @property
    def spring_running(self) -> bool:
        return self._spring.running

    @property
    def roll_actuator(self) -> bool:
        return DIJOFS_X in self.ffb_axes

    @property
    def pitch_actuator(self) -> bool:
        return DIJOFS_Y in self.ffb_axes

    def enumerate(self):
        try:
            di = create_direct_input()
            return enum_devices(di, only_attached=True, only_force_feedback=True)
        except Exception as exc:
            self.last_error = f"enumerate: {exc}"
            log.error("enumerate", exc)
            return []

    def connect(self, guid_instance, hwnd) -> bool:
        self.disconnect()
        self._hwnd = hwnd
        try:
            self._di = create_direct_input()
            self._device = create_device(self._di, guid_instance)
            set_cooperative_level(self._device, hwnd=hwnd, exclusive=True, background=True)

            self.ffb_axes = enum_ffb_axes_actuator_offsets(self._device) or [DIJOFS_X, DIJOFS_Y]
            self.ffb_axes = [a for a in self.ffb_axes if a in (DIJOFS_X, DIJOFS_Y)]
            if not self.ffb_axes:
                self.ffb_axes = [DIJOFS_X]
            axis_subset = self.ffb_axes[:2]
            for axis in axis_subset:
                try:
                    set_axis_range(self._device, axis, -AXIS_RANGE, AXIS_RANGE)
                except Exception as exc:
                    log.warn(f"axis range failed for {axis}: {exc}")

            self._data_format = set_data_format(
                self._device, build_joystick_data_format(tuple(axis_subset)))
            acquire(self._device)
            try:
                stop_all_effects(self._device)
            except Exception as exc:
                log.warn(f"stop-all failed: {exc}")
            try:
                set_autocenter(self._device, False)
            except Exception:
                pass
            try:
                self.gain = get_device_gain(self._device)
            except Exception:
                pass
            self.device_name = "device"
            self.last_error = ""
            log.info(f"connected (axes={axis_subset})")
            return True
        except Exception as exc:
            self.last_error = str(exc)
            log.error("connect", exc)
            self.disconnect()
            return False

    def disconnect(self) -> None:
        self.stop_all()
        self._main.dispose()
        self._spring.dispose()
        if self._device is not None:
            try:
                unacquire(self._device)
            except Exception:
                pass
        self._device = None
        self._di = None
        self._data_format = None
        self._hwnd = None
        self.device_name = "(not connected)"

    def set_device_gain(self, gain: int) -> None:
        self.gain = gain
        if self._device is not None:
            try:
                set_device_gain(self._device, gain)
            except Exception as exc:
                self.last_error = f"gain: {exc}"
                log.warn(str(exc))

    def get_device_gain(self) -> int:
        if self._device is None:
            return self.gain
        try:
            return get_device_gain(self._device)
        except Exception:
            return self.gain

    def poll(self) -> PollResult:
        if self._device is None:
            return PollResult(False, 0, 0, 0.0, 0.0)
        try:
            self._device.Poll()
            state = DIJOYSTATE()
            self._device.GetDeviceState(C.sizeof(DIJOYSTATE), C.byref(state))
            raw_roll = getattr(state, "lX", 0)
            raw_pitch = getattr(state, "lY", 0)
            buttons = 0
            for i, b in enumerate(state.rgbButtons[:32]):
                if b:
                    buttons |= 1 << i
            return PollResult(True, raw_roll, raw_pitch,
                              raw_roll / AXIS_RANGE, raw_pitch / AXIS_RANGE, buttons)
        except Exception as exc:
            self.last_error = f"poll: {exc}"
            try:
                acquire(self._device)
            except Exception:
                pass
            return PollResult(False, 0, 0, 0.0, 0.0)

    # ---- slots -----------------------------------------------------------

    def _effects_axes_and_dirs(self, spec: EffectSpec):
        if spec.is_condition:
            axes_offsets = select_condition_axes(
                spec.apply_roll, spec.apply_pitch, self.roll_actuator, self.pitch_actuator,
                self.ffb_axes)
            directions = [0] * len(axes_offsets)
        else:
            axes_offsets = list(self.ffb_axes)
            cx, cy = direction_components(spec.direction_deg)
            directions = [round((cy if a == DIJOFS_Y else cx) * AXIS_RANGE) for a in axes_offsets]
            if len(axes_offsets) == 1:
                directions = [0]  # library convention: 1-axis uses CARTESIAN {0}
        return axes_offsets, directions

    def _build_kwargs(self, spec: EffectSpec):
        axes_offsets, _ = self._effects_axes_and_dirs(spec)
        kwargs = dict(axes_offsets=tuple(axes_offsets))
        if spec.is_condition:
            # conditions: polar {0,0} (library default "must not be rotated")
            kwargs["direction_basis"] = DIEFF_POLAR
            kwargs["direction_hundredths_deg"] = 0
            kwargs["per_axis"] = [
                dict(offset=spec.center_offset_x if i == 0 else spec.center_offset_y,
                     positive_coefficient=spec.positive_coefficient,
                     negative_coefficient=spec.negative_coefficient,
                     positive_saturation=spec.positive_saturation,
                     negative_saturation=spec.negative_saturation,
                     dead_band=spec.dead_band)
                for i in range(len(axes_offsets))
            ]
        else:
            kwargs["direction_basis"] = DIEFF_CARTESIAN
            kwargs["direction_hundredths_deg"] = spec.direction_deg * 100
            kwargs["magnitude"] = spec.magnitude if spec.effect != FfbEffect.RAMP_FORCE else None
            kwargs["duration_us"] = (spec.duration_ms * 1000) if spec.duration_ms > 0 else 0xFFFFFFFF
            if spec.effect == FfbEffect.RAMP_FORCE:
                kwargs["start_magnitude"] = spec.ramp_start
                kwargs["end_magnitude"] = spec.ramp_end
                kwargs.pop("magnitude")
            if spec.is_periodic:
                kwargs["offset"] = spec.periodic_offset
                kwargs["phase_hundredths_deg"] = ((spec.phase_deg % 360) + 360) % 360 * 100
                kwargs["period_us"] = max(1, spec.period_ms) * 1000
            if spec.use_envelope:
                kwargs["attack_level"] = spec.attack_level
                kwargs["attack_time_ms"] = spec.attack_ms
                kwargs["fade_level"] = spec.fade_level
                kwargs["fade_time_ms"] = spec.fade_ms
        return kwargs

    def _apply_slot(self, slot: _Slot, spec: EffectSpec) -> None:
        if self._device is None:
            self.last_error = "not connected"
            return
        try:
            axes_offsets, _ = self._effects_axes_and_dirs(spec)
            if slot.fx is None or slot.last_type != spec.effect or slot.last_axes != tuple(axes_offsets):
                slot.dispose()
                factory = EFFECT_GUID_FACTORY[spec.effect]
                slot.fx = factory(self._device, **self._build_kwargs(spec))
                slot.last_type = spec.effect
                slot.last_axes = tuple(axes_offsets)
                if slot.running:
                    self._start(slot)
                return
            slot.fx.apply(
                duration_ms=spec.duration_ms,
                direction_hundredths_deg=spec.direction_deg * 100 if not spec.is_condition else None,
                type_specific=self._live_type_specific(spec) if not spec.is_condition else None,
            )
        except Exception as exc:
            self.last_error = f"{slot.name}: {exc}"
            log.error(f"{slot.name} apply", exc)

    def _live_type_specific(self, spec: EffectSpec):
        from directinput_ffb.dinput_definitions import (
            DICONSTANTFORCE, DIRAMPFORCE, DIPERIODIC,
        )
        if spec.effect == FfbEffect.CONSTANT_FORCE:
            return DICONSTANTFORCE(lMagnitude=spec.magnitude)
        if spec.effect == FfbEffect.RAMP_FORCE:
            return DIRAMPFORCE(lStart=spec.ramp_start, lEnd=spec.ramp_end)
        return DIPERIODIC(
            dwMagnitude=spec.magnitude, lOffset=spec.periodic_offset,
            dwPhase=((spec.phase_deg % 360) + 360) % 360 * 100,
            dwPeriod=max(1, spec.period_ms) * 1000)

    def _start(self, slot: _Slot) -> None:
        if slot.fx is not None:
            slot.fx.download()
            slot.fx.start(iterations=1)
            slot.running = True

    def _slot_start(self, slot: _Slot) -> None:
        if self._device is None:
            return
        try:
            self._start(slot)
        except Exception as exc:
            self.last_error = f"{slot.name}: {exc}"
            log.error(f"{slot.name} start", exc)

    def _slot_stop(self, slot: _Slot) -> None:
        if slot.fx is not None:
            try:
                slot.fx.stop()
            except Exception as exc:
                log.warn(f"{slot.name} stop: {exc}")
            slot.running = False

    def apply_main(self, spec: EffectSpec) -> None:
        self._apply_slot(self._main, spec)

    def start_main(self) -> None:
        self._slot_start(self._main)

    def stop_main(self) -> None:
        self._slot_stop(self._main)

    def apply_spring(self, spec: EffectSpec) -> None:
        self._apply_slot(self._spring, spec)

    def start_spring(self) -> None:
        self._slot_start(self._spring)

    def stop_spring(self) -> None:
        self._slot_stop(self._spring)

    def stop_all(self) -> None:
        self._slot_stop(self._main)
        self._slot_stop(self._spring)


__all__ = ["DeviceSession", "PollResult", "select_condition_axes", "AXIS_RANGE"]
````

- [ ] **Step 2: Create `tests/test_device.py`**

````python
import unittest
from directinput_ffb_tester.device import DeviceSession, select_condition_axes
from directinput_ffb.dinput_definitions import DIJOFS_X, DIJOFS_Y


class TestConditionAxes(unittest.TestCase):
    def test_two_axis(self):
        self.assertEqual(select_condition_axes(True, True, True, True, [DIJOFS_X, DIJOFS_Y]),
                         [DIJOFS_X, DIJOFS_Y])

    def test_wheel_no_pitch(self):
        self.assertEqual(select_condition_axes(True, True, True, False, [DIJOFS_X]),
                         [DIJOFS_X])

    def test_both_off_fallback(self):
        self.assertEqual(select_condition_axes(False, False, True, True, [DIJOFS_X]),
                         [DIJOFS_X])


class TestNoDevice(unittest.TestCase):
    def test_enumerate_returns_list(self):
        s = DeviceSession()
        self.assertIsInstance(s.enumerate(), list)

    def test_poll_not_connected(self):
        s = DeviceSession()
        p = s.poll()
        self.assertFalse(p.ok)
        self.assertFalse(s.connected)


if __name__ == "__main__":
    unittest.main()
````

- [ ] **Step 3: Run and verify it passes**

Run: `python -m unittest tests.test_device -v`
Expected: 5 tests PASS (the no-device ones exercise the real `create_direct_input`/`enum_devices`; on a machine with FFB hardware `enumerate()` may return a non-empty list, which the test tolerates).

---

### Task 7: views.py �� YokeView, SliderRow, DirPad, CollapsibleGroup

**Files:**
- Create: `directinput_ffb_tester/views.py`, `tests/test_views.py`

**Interfaces:**
- Produces:
  - `YokeView(QWidget)` with `set_state(roll_norm, pitch_norm, force_x, force_y, command_direction_deg, device_connected)` and `rotation_range_deg` property.
  - `SliderRow(QWidget)` �� `(label, minimum, maximum, value, increment=1, vertical=False)`; `.value()`, `.set_value(v)`, `.set_enabled(on)`, `valueChanged = pyqtSignal(int)`, `.set_label_row_control(w)`.
  - `DirPad(QWidget)` �� `change_requested = pyqtSignal(int)` (degrees).
  - `CollapsibleGroup(QGroupBox)` �� `set_body_enabled(on)`, caption-click collapse.

- [ ] **Step 1: Create `directinput_ffb_tester/views.py`**

````python
"""Qt widgets: yoke visualisation, slider rows, compass pad, collapsible groups."""
from __future__ import annotations

import math

from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QPixmap, QTransform
from PyQt6.QtWidgets import (
    QGroupBox, QHBoxLayout, QLabel, QPushButton, QSlider, QSpinBox, QVBoxLayout,
    QWidget, QGridLayout,
)

BG = QColor(0x12, 0x15, 0x1a)
GRID = QColor(0x27, 0x2c, 0x36)
YOKE = QColor(0xcc, 0xd2, 0xdc)
YOKE_DIM = QColor(0x6a, 0x72, 0x82)
HUB = QColor(0x9a, 0xa4, 0xb2)
FX_COL = QColor(0x22, 0xd3, 0xee)
FY_COL = QColor(0xa7, 0x8b, 0xfa)
F_COL = QColor(0x38, 0xbd, 0xf8)
POS_COL = QColor(0xfa, 0xcc, 0x15)
TEXT_COL = QColor(0xb6, 0xbe, 0xca)

MONO = "Consolas"


def _clamp1(v: float) -> float:
    return max(-1.0, min(1.0, v))


class YokeView(QWidget):
    """Front-on yoke/wheel drawing with commanded force arrows (port of DeviceView)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumSize(300, 240)
        self._roll = 0.0
        self._pitch = 0.0
        self._fx = 0.0
        self._fy = 0.0
        self._cmd_deg = float("nan")
        self._connected = False
        self.rotation_range_deg = 180.0

    def set_state(self, roll_norm, pitch_norm, force_x, force_y,
                  command_direction_deg, device_connected) -> None:
        self._roll = _clamp1(roll_norm)
        self._pitch = _clamp1(pitch_norm)
        self._fx = force_x
        self._fy = force_y
        self._cmd_deg = command_direction_deg
        self._connected = device_connected
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), BG)
        w, h = self.width(), self.height()
        cx = w * 0.5
        cy = h * 0.52
        unit = min(w, h) * 0.30
        self._draw_reference(p, cx, cy, unit)
        self._draw_yoke(p, cx, cy, unit)
        self._draw_forces(p, cx, cy, unit)
        self._draw_position_map(p, QRectF(w - 138, h - 156, 112, 112))
        self._draw_axis_labels(p, cx, cy, unit)
        if not self._connected:
            p.setPen(QColor(0xf8, 0x71, 0x71))
            p.drawText(14, h - 24, "device not connected - showing commanded force only")

    def _draw_reference(self, p, cx, cy, unit):
        dash = QPen(GRID, 1)
        dash.setStyle(Qt.PenStyle.DashLine)
        p.setPen(dash)
        p.drawLine(QPointF(cx - unit * 1.6, cy), QPointF(cx + unit * 1.6, cy))
        p.drawLine(QPointF(cx, cy - unit * 1.4), QPointF(cx, cy + unit * 1.4))
        p.setPen(QPen(GRID, 1))
        r = unit * 0.5
        while r <= unit * 1.5:
            p.drawEllipse(QPointF(cx, cy), r, r)
            r += unit * 0.5

    def _draw_yoke(self, p, cx, cy, unit):
        pitch_shift = self._pitch * unit * 0.42
        scale = 1.0 + self._pitch * 0.13
        t = QTransform()
        t.translate(cx, cy + pitch_shift)
        t.scale(scale, scale)
        t.rotate(self._roll * self.rotation_range_deg / 2.0)
        p.setTransform(t)
        rim = unit
        thick = max(3.0, unit * 0.055)
        pen = QPen(YOKE, thick)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawLine(QPointF(0, -rim * 0.25), QPointF(0, -rim * 1.5))
        p.drawArc(QRectF(-rim, -rim, rim * 2, rim * 2), 125 * 16, 290 * 16)
        p.drawLine(QPointF(-rim * 0.98, 0), QPointF(rim * 0.98, 0))
        gw = unit * 0.16
        gh = unit * 0.5
        p.setBrush(QBrush(YOKE))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(-rim * 0.98 - gw, -gh / 2, gw * 2, gh), gw * 0.6, gw * 0.6)
        p.drawRoundedRect(QRectF(rim * 0.98 - gw, -gh / 2, gw * 2, gh), gw * 0.6, gw * 0.6)
        hr = unit * 0.17
        p.setBrush(QBrush(HUB))
        p.drawEllipse(QPointF(0, 0), hr, hr)
        p.setPen(QPen(YOKE_DIM, thick * 0.5))
        p.drawEllipse(QPointF(0, 0), hr, hr)
        p.resetTransform()

    def _draw_forces(self, p, cx, cy, unit):
        hub_y = cy + self._pitch * unit * 0.42
        hub = QPointF(cx, hub_y)
        fx = self._fx / 10000.0
        fy = self._fy / 10000.0
        length = unit * 1.35
        font = QFont(MONO, 9)
        if abs(fx) > 0.01:
            pen = QPen(FX_COL, 4)
            to = QPointF(hub.x() + fx * length, hub.y())
            self._arrow(p, pen, FX_COL, hub, to)
        if abs(fy) > 0.01:
            pen = QPen(FY_COL, 4)
            to = QPointF(hub.x(), hub.y() + fy * length)
            self._arrow(p, pen, FY_COL, hub, to)
        mag = math.hypot(fx, fy)
        if mag > 0.01:
            pen = QPen(F_COL, 6)
            to = QPointF(hub.x() + fx * length, hub.y() + fy * length)
            self._arrow(p, pen, F_COL, hub, to)
        p.setFont(font)
        p.setPen(FX_COL)
        p.drawText(QPointF(cx + unit * 0.9, cy - unit * 1.32), f"Fx {self._fx:+7.0f}")
        p.setPen(FY_COL)
        p.drawText(QPointF(cx + unit * 0.9, cy - unit * 1.18), f"Fy {self._fy:+7.0f}")
        p.setPen(F_COL)
        p.drawText(QPointF(cx + unit * 0.9, cy - unit * 1.04), f"|F| {mag * 10000:6.0f}")
        if not math.isnan(self._cmd_deg):
            p.setPen(TEXT_COL)
            p.drawText(QPointF(cx + unit * 0.9, cy - unit * 0.90), f"cmd {self._cmd_deg:5.1f} deg")

    def _arrow(self, p, pen, color, frm, to):
        p.setPen(pen)
        p.drawLine(frm, to)
        a = math.atan2(to.y() - frm.y(), to.x() - frm.x())
        hs = 11.0
        p1 = QPointF(to.x() - hs * math.cos(a - 0.5), to.y() - hs * math.sin(a - 0.5))
        p2 = QPointF(to.x() - hs * math.cos(a + 0.5), to.y() - hs * math.sin(a + 0.5))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(color))
        p.drawPolygon([to, p1, p2])

    def _draw_position_map(self, p, box):
        p.setPen(QPen(GRID, 1))
        p.drawRect(box)
        p.drawLine(QPointF(box.x(), box.y() + box.height() / 2),
                   QPointF(box.right(), box.y() + box.height() / 2))
        p.drawLine(QPointF(box.x() + box.width() / 2, box.y()),
                   QPointF(box.x() + box.width() / 2, box.bottom()))
        px = box.x() + box.width() / 2 + self._roll * box.width() / 2 * 0.92
        py = box.y() + box.height() / 2 + self._pitch * box.height() / 2 * 0.92
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(POS_COL))
        p.drawEllipse(QPointF(px, py), 4, 4)
        p.setPen(TEXT_COL)
        p.setFont(QFont(MONO, 8))
        p.drawText(QPointF(box.x() + 1, box.y() - 4), "position")
        p.drawText(QPointF(box.x() + 1, box.bottom() + 12),
                   f"R {self._roll:+5.2f}   P {self._pitch:+5.2f}")

    def _draw_axis_labels(self, p, cx, cy, unit):
        f = QFont(MONO, 8, QFont.Weight.Bold)
        p.setFont(f)
        p.setPen(TEXT_COL)
        p.drawText(QPointF(cx - unit * 1.6, cy - 4), "ROLL -  (left)")
        p.drawText(QPointF(cx + unit * 1.6 - 110, cy - 4), "ROLL +  (right)")
        p.drawText(QPointF(cx - 90, cy - unit * 1.4), "PITCH -  (push / nose-down)")
        p.drawText(QPointF(cx - 82, cy + unit * 1.32), "PITCH +  (pull / nose-up)")


class SliderRow(QWidget):
    valueChanged = pyqtSignal(int)

    def __init__(self, label: str, minimum: int, maximum: int, value: int,
                 increment: int = 1, vertical: bool = False, parent=None) -> None:
        super().__init__(parent)
        self._label = QLabel(label)
        self._bar = QSlider(Qt.Orientation.Horizontal)
        self._bar.setRange(minimum, maximum)
        self._bar.setSingleStep(increment)
        self._bar.setPageStep(max(increment, (maximum - minimum) // 10))
        self._num = QSpinBox()
        self._num.setRange(minimum, maximum)
        self._num.setSingleStep(increment)
        self._num.setValue(value)
        self._bar.setValue(value)
        self._bar.valueChanged.connect(self._from_bar)
        self._num.valueChanged.connect(self._from_num)

        root = QGridLayout()
        root.setContentsMargins(0, 0, 0, 0)
        if vertical:
            root.addWidget(self._label, 0, 0, 1, 2)
            root.addWidget(self._bar, 1, 0)
            root.addWidget(self._num, 1, 1)
            root.setColumnStretch(0, 1)
        else:
            root.addWidget(self._label, 0, 0)
            root.addWidget(self._bar, 0, 1)
            root.addWidget(self._num, 0, 2)
            root.setColumnStretch(1, 1)
            root.setColumnMinimumWidth(0, 128)
        self.setLayout(root)
        self.setMinimumHeight(46 if vertical else 30)

    def _from_bar(self, v: int) -> None:
        self._num.setValue(v)
        self.valueChanged.emit(v)

    def _from_num(self, v: int) -> None:
        self._bar.setValue(v)
        self.valueChanged.emit(v)

    def value(self) -> int:
        return self._num.value()

    def set_value(self, v: int) -> None:
        v = max(self._num.minimum(), min(self._num.maximum(), int(v)))
        self._num.setValue(v)
        self._bar.setValue(v)

    def set_enabled(self, enabled: bool) -> None:
        self._bar.setEnabled(enabled)
        self._num.setEnabled(enabled)

    def set_label_row_control(self, w: QWidget) -> None:
        self.layout().addWidget(w, 0, 2)


class DirPad(QWidget):
    change_requested = pyqtSignal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        self._readout = QLabel("270 deg")
        self._readout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(self._button("push 180", 180), 0, 1)
        grid.addWidget(self._button("left 90", 90), 1, 0)
        grid.addWidget(self._readout, 1, 1)
        grid.addWidget(self._button("right 270", 270), 1, 2)
        grid.addWidget(self._button("pull 0", 0), 2, 1)
        for c in range(3):
            grid.setColumnStretch(c, 1)
            grid.setRowStretch(c, 1)
        self.setLayout(grid)
        self.setMinimumHeight(84)

    def _button(self, text: str, deg: int) -> QPushButton:
        b = QPushButton(text)
        b.clicked.connect(lambda: self.change_requested.emit(deg))
        return b

    def set_readout(self, deg: int) -> None:
        self._readout.setText(f"{deg} deg")

    def set_enabled(self, enabled: bool) -> None:
        for b in self.findChildren(QPushButton):
            b.setEnabled(enabled)


class CollapsibleGroup(QGroupBox):
    def __init__(self, title: str, height: int, collapsible: bool = True, parent=None) -> None:
        super().__init__(title, parent)
        self._title = title
        self._open_height = height
        self._collapsible = collapsible
        self._collapsed = False
        self.setMinimumHeight(height)
        self._update_caption()

    def _update_caption(self) -> None:
        if self._collapsible:
            self.setTitle((">  " if self._collapsed else "v  ") + self._title)
        else:
            self.setTitle(self._title)

    def mousePressEvent(self, event) -> None:
        if self._collapsible and event.button() == Qt.MouseButton.LeftButton and event.position().y() <= 20:
            self.toggle_collapsed()
        else:
            super().mousePressEvent(event)

    def toggle_collapsed(self) -> None:
        if not self._collapsible:
            return
        self._collapsed = not self._collapsed
        for w in self.findChildren(QWidget):
            w.setVisible(not self._collapsed)
        self.setMinimumHeight(22 if self._collapsed else self._open_height)
        self._update_caption()

    def set_body_enabled(self, on: bool) -> None:
        for w in self.findChildren(QWidget):
            w.setEnabled(on)
        self.setStyleSheet("" if on else "QGroupBox { color: gray; }")


__all__ = ["YokeView", "SliderRow", "DirPad", "CollapsibleGroup"]
````

- [ ] **Step 2: Create `tests/test_views.py`**

````python
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import unittest
from PyQt6.QtWidgets import QApplication, QCheckBox

_app = QApplication.instance() or QApplication([])


class TestViews(unittest.TestCase):
    def test_yoke_paint(self):
        from directinput_ffb_tester.views import YokeView
        v = YokeView()
        v.resize(400, 300)
        v.set_state(0.5, -0.3, 4000, -2000, 45.0, True)
        pix = v.grab()
        self.assertTrue(pix.width() > 0 and pix.height() > 0)

    def test_slider_row_sync(self):
        from directinput_ffb_tester.views import SliderRow
        r = SliderRow("Mag", -10000, 10000, 5000, increment=100)
        r._num.setValue(7000)
        self.assertEqual(r._bar.value(), 7000)
        self.assertEqual(r.value(), 7000)
        r.set_value(-100)
        self.assertEqual(r.value(), -100)
        r.set_enabled(False)

    def test_dirpad_signal(self):
        from PyQt6.QtWidgets import QPushButton
        from directinput_ffb_tester.views import DirPad
        d = DirPad()
        got = []
        d.change_requested.connect(got.append)
        for b in d.findChildren(QPushButton):
            b.click()
        self.assertEqual(len(got), 5)

    def test_collapsible(self):
        from directinput_ffb_tester.views import CollapsibleGroup
        g = CollapsibleGroup("t", 200)
        g.toggle_collapsed()
        self.assertTrue(g._collapsed)


if __name__ == "__main__":
    unittest.main()
````

- [ ] **Step 3: Run and verify it passes**

Run: `python -m unittest tests.test_views -v`
Expected: 4 tests PASS. (Fix the DirPad test to use `from PyQt6.QtWidgets import QPushButton` at module top in a real cleanup pass; the plan's inline import is a simplification.)

---

### Task 8: window.py �� MainWindow + __main__.py

**Files:**
- Create: `directinput_ffb_tester/window.py`, `directinput_ffb_tester/__init__.py` (empty), `directinput_ffb_tester/__main__.py`, `tests/test_window.py`

**Interfaces:**
- Consumes: Tasks 1-7.
- Produces: `MainWindow(QMainWindow)` �� `rescan_devices()`, `connect_selected()`, `close_device()`, `stop_active_effects()`, `winId()`-based HWND; app entry in `__main__.py`.

- [ ] **Step 1: Create `directinput_ffb_tester/__init__.py`**

````python
"""PyQt6 FFB test tool on top of directinput_ffb (port of barsk/FFBTestTool)."""
__all__ = ["__version__"]
__version__ = "1.0.0"
````

- [ ] **Step 2: Create `directinput_ffb_tester/window.py`**

````python
"""Main window of the FFB test tool."""
from __future__ import annotations

import time
from typing import Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QLabel, QMainWindow, QPlainTextEdit, QPushButton,
    QScrollArea, QSpinBox, QSplitter, QVBoxLayout, QWidget, QHBoxLayout,
    QMessageBox,
)

from directinput_ffb.dinput_definitions import DIJOFS_X, DIJOFS_Y

from . import log
from .spec import FfbEffect, EffectSpec, ForceModel, Kinematics, Pretty, DirWord
from .views import YokeView, SliderRow, DirPad, CollapsibleGroup
from .device import DeviceSession

MAIN_EFFECTS = [e for e in FfbEffect if e is not FfbEffect.SPRING]


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("py_directinput_ffb - FFB Test Tool")
        self.resize(1280, 860)
        self.setMinimumSize(1040, 680)

        self.dev = DeviceSession()
        self.ctx_poll = self.dev

        self._spring_dirty = False
        self._main_dirty = False
        self._last_roll = self._last_pitch = 0.0
        self._last_vel_r = self._last_vel_p = 0.0
        self._last_t = time.monotonic()
        self._frame = 0
        self._effect_started: Optional[float] = None

        self._build_widgets()
        self._wire_events()
        self.rescan_devices()

        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    # ------------------------------------------------------------------ UI

    def _build_widgets(self) -> None:
        self._view = YokeView()

        self._debug = QPlainTextEdit()
        self._debug.setReadOnly(True)
        self._debug.setFont(QFont("Consolas", 9))
        self._debug.setFixedHeight(210)
        self._debug.setStyleSheet("background: #14171c; color: #c4d0c4;")

        self._rotation_range = QSpinBox()
        self._rotation_range.setRange(10, 3600)
        self._rotation_range.setValue(180)
        self._rotation_range.setSuffix(" deg")

        self._invert_view = QCheckBox("invert roll/pitch view (display only)")
        self._invert_view.setChecked(False)

        left = QWidget()
        lv = QVBoxLayout()
        lv.setContentsMargins(0, 0, 0, 0)
        strip = QHBoxLayout()
        strip.addWidget(QLabel("Device rotation range"))
        strip.addWidget(self._rotation_range)
        strip.addStretch(1)
        strip.addWidget(self._invert_view)
        lv.addLayout(strip)
        lv.addWidget(self._view, 1)
        lv.addWidget(self._debug)
        left.setLayout(lv)

        right = QScrollArea()
        right.setWidgetResizable(True)
        self._flow = QWidget()
        fv = QVBoxLayout(self._flow)
        fv.setContentsMargins(8, 8, 8, 8)

        # Device group
        self._cbo_device = QComboBox()
        self._cbo_device.setMinimumWidth(260)
        self._btn_rescan = QPushButton("Rescan")
        self._btn_connect = QPushButton("Connect")
        self._btn_log = QPushButton("Open log")
        self._status = QLabel("No device opened")
        self._gain = SliderRow("Device gain", 0, 10000, 10000, 100)
        gdev = CollapsibleGroup("Device", 150, collapsible=False)
        d2 = QVBoxLayout(gdev)
        row = QHBoxLayout()
        row.addWidget(self._cbo_device)
        row.addWidget(self._btn_rescan)
        row.addWidget(self._btn_connect)
        row.addWidget(self._btn_log)
        d2.addLayout(row)
        d2.addWidget(self._status)
        d2.addWidget(self._gain)
        fv.addWidget(gdev)

        # Spring group
        self._chk_spring_on = QCheckBox("on  (centring safeguard)")
        self._chk_spring_on.setChecked(True)
        self._spring_mag = SliderRow("Magnitude", 0, 10000, 8000, 100, vertical=True)
        self._spring_offx = SliderRow("Offset X", -10000, 10000, 0, 100, vertical=True)
        self._spring_offy = SliderRow("Offset Y", -10000, 10000, 0, 100, vertical=True)
        gspring = CollapsibleGroup("Spring Effect", 210, collapsible=False)
        s2 = QVBoxLayout(gspring)
        s2.addWidget(self._chk_spring_on)
        for w in (self._spring_mag, self._spring_offx, self._spring_offy):
            s2.addWidget(w)
        fv.addWidget(gspring)

        # Effect group
        self._chk_effect_on = QCheckBox("on")
        self._cbo_effect = QComboBox()
        for e in MAIN_EFFECTS:
            self._cbo_effect.addItem(Pretty(e), e)
        self._cbo_effect.setCurrentIndex(0)
        self._magnitude = SliderRow("Magnitude", 0, 10000, 4000, 100, vertical=True)
        self._direction = SliderRow("Direction deg", 0, 359, 270, 5, vertical=True)
        self._dir_pad = DirPad()
        self._duration = SliderRow("Duration ms", 0, 20000, 1500, 100, vertical=True)
        self._chk_infinite = QCheckBox("inf")
        self._chk_infinite.setChecked(True)
        self._duration.set_label_row_control(self._chk_infinite)
        geffect = CollapsibleGroup("Effect", 320, collapsible=False)
        e2 = QVBoxLayout(geffect)
        erow = QHBoxLayout()
        erow.addWidget(self._chk_effect_on)
        erow.addWidget(self._cbo_effect, 1)
        e2.addLayout(erow)
        for w in (self._magnitude, self._direction, self._dir_pad, self._duration):
            e2.addWidget(w)
        fv.addWidget(geffect)

        # Periodic / Ramp / Condition / Envelope
        self._period = SliderRow("Period ms", 20, 5000, 1500, 20)
        self._phase = SliderRow("Phase deg", 0, 359, 0, 5)
        self._p_offset = SliderRow("Offset", -10000, 10000, 0, 100)
        self._grp_periodic = CollapsibleGroup("Periodic", 160)
        p2 = QVBoxLayout(self._grp_periodic)
        for w in (self._period, self._phase, self._p_offset):
            p2.addWidget(w)
        fv.addWidget(self._grp_periodic)

        self._ramp_start = SliderRow("Ramp start", -10000, 10000, 0, 100)
        self._ramp_end = SliderRow("Ramp end", -10000, 10000, 8000, 100)
        self._ramp_duration = SliderRow("Ramp duration ms", 0, 20000, 1500, 100)
        self._grp_ramp = CollapsibleGroup("Ramp force", 160)
        r2 = QVBoxLayout(self._grp_ramp)
        for w in (self._ramp_start, self._ramp_end, self._ramp_duration):
            r2.addWidget(w)
        fv.addWidget(self._grp_ramp)

        self._pos_coef = SliderRow("Pos coeff", -10000, 10000, 6000, 100)
        self._neg_coef = SliderRow("Neg coeff", -10000, 10000, 6000, 100)
        self._pos_sat = SliderRow("Pos sat", 0, 10000, 10000, 100)
        self._neg_sat = SliderRow("Neg sat", 0, 10000, 10000, 100)
        self._dead_band = SliderRow("Dead band", 0, 10000, 0, 100)
        self._center = SliderRow("Centre offset", -10000, 10000, 0, 100)
        self._chk_roll = QCheckBox("roll (X)")
        self._chk_roll.setChecked(True)
        self._chk_pitch = QCheckBox("pitch (Y)")
        self._chk_pitch.setChecked(True)
        self._grp_condition = CollapsibleGroup("Condition", 280)
        c2 = QVBoxLayout(self._grp_condition)
        for w in (self._pos_coef, self._neg_coef, self._pos_sat, self._neg_sat,
                  self._dead_band, self._center):
            c2.addWidget(w)
        axes_row = QHBoxLayout()
        axes_row.addWidget(self._chk_roll)
        axes_row.addWidget(self._chk_pitch)
        c2.addLayout(axes_row)
        fv.addWidget(self._grp_condition)

        self._chk_envelope = QCheckBox("use envelope")
        self._atk_level = SliderRow("Attack level", 0, 10000, 0, 100)
        self._atk_time = SliderRow("Attack ms", 0, 5000, 200, 20)
        self._fade_level = SliderRow("Fade level", 0, 10000, 0, 100)
        self._fade_time = SliderRow("Fade ms", 0, 5000, 200, 20)
        self._grp_envelope = CollapsibleGroup("Envelope (constant/ramp/periodic)", 220)
        v2 = QVBoxLayout(self._grp_envelope)
        v2.addWidget(self._chk_envelope)
        for w in (self._atk_level, self._atk_time, self._fade_level, self._fade_time):
            v2.addWidget(w)
        fv.addWidget(self._grp_envelope)
        fv.addStretch(1)

        right.setWidget(self._flow)
        split = QSplitter()
        split.addWidget(left)
        split.addWidget(right)
        split.setSizes([600, 600])
        self.setCentralWidget(split)

    def _wire_events(self) -> None:
        self._btn_rescan.clicked.connect(self.rescan_devices)
        self._btn_connect.clicked.connect(self.connect_selected)
        self._btn_log.clicked.connect(log.open_in_editor)
        self._cbo_effect.currentIndexChanged.connect(self._on_effect_change)
        self._cbo_effect.currentIndexChanged.connect(self._mark_main_dirty)
        self._chk_infinite.toggled.connect(self._mark_main_dirty)
        self._chk_envelope.toggled.connect(self._on_envelope_toggle)
        self._chk_envelope.toggled.connect(self._mark_main_dirty)
        self._chk_roll.toggled.connect(self._mark_main_dirty)
        self._chk_pitch.toggled.connect(self._mark_main_dirty)
        for sr in (self._magnitude, self._direction, self._duration, self._period,
                   self._phase, self._p_offset, self._ramp_start, self._ramp_end,
                   self._ramp_duration, self._pos_coef, self._neg_coef, self._pos_sat,
                   self._neg_sat, self._dead_band, self._center, self._atk_level,
                   self._atk_time, self._fade_level, self._fade_time):
            sr.valueChanged.connect(self._mark_main_dirty)
        for sr in (self._spring_mag, self._spring_offx, self._spring_offy):
            sr.valueChanged.connect(self._mark_spring_dirty)
        self._dir_pad.change_requested.connect(self._on_dir_pad)
        self._chk_spring_on.toggled.connect(self._on_spring_toggle)
        self._chk_effect_on.toggled.connect(self._on_effect_toggle)
        self._gain.valueChanged.connect(self._on_gain_change)
        self._rotation_range.valueChanged.connect(
            lambda _v: setattr(self._view, "rotation_range_deg", float(self._rotation_range.value())))
        self._invert_view.toggled.connect(self._invert_view_toggled)

    # ------------------------------------------------------------- events

    def _on_dir_pad(self, deg: int) -> None:
        self._direction.set_value(deg)
        self._mark_main_dirty()

    def _mark_main_dirty(self, *_args) -> None:
        self._main_dirty = True

    def _mark_spring_dirty(self, *_args) -> None:
        self._spring_dirty = True

    def _on_effect_change(self, *_args) -> None:
        self._update_group_enable()
        self._main_dirty = True

    def _on_envelope_toggle(self, *_args) -> None:
        on = self._chk_envelope.isChecked()
        for sr in (self._atk_level, self._atk_time, self._fade_level, self._fade_time):
            sr.set_enabled(on)
        self._main_dirty = True

    def _on_gain_change(self, value: int) -> None:
        self.dev.set_device_gain(value)

    def _on_spring_toggle(self, checked: bool) -> None:
        try:
            if checked:
                self.dev.apply_spring(self._spring_spec())
                self.dev.start_spring()
                log.info("spring ON")
            else:
                self.dev.stop_spring()
                log.info("spring OFF")
        except Exception as exc:
            self._show(f"spring toggle failed: {exc}")

    def _on_effect_toggle(self, checked: bool) -> None:
        try:
            if checked:
                spec = self._main_spec()
                self.dev.apply_main(spec)
                self.dev.start_main()
                self._effect_started = time.monotonic()
                log.info(f"effect ON: {spec.effect.value} dir={spec.direction_deg} mag={spec.magnitude}")
            else:
                self.dev.stop_main()
                self._effect_started = None
                log.info("effect OFF")
        except Exception as exc:
            self._show(f"effect toggle failed: {exc}")

    def _show(self, msg: str) -> None:
        self._status.setText(msg)
        log.warn(msg)

    # ---------------------------------------------------------------- specs

    def _selected_effect(self) -> FfbEffect:
        return self._cbo_effect.currentData()

    def _spring_spec(self) -> EffectSpec:
        return EffectSpec(
            effect=FfbEffect.SPRING,
            positive_coefficient=self._spring_mag.value(),
            negative_coefficient=self._spring_mag.value(),
            dead_band=0,
            center_offset_x=self._spring_offx.value(),
            center_offset_y=self._spring_offy.value(),
        )

    def _main_spec(self) -> EffectSpec:
        e = self._selected_effect()
        ramp = e is FfbEffect.RAMP_FORCE
        return EffectSpec(
            effect=e,
            direction_deg=self._direction.value(),
            magnitude=self._magnitude.value(),
            duration_ms=(self._ramp_duration.value() if ramp
                         else (0 if self._chk_infinite.isChecked() else self._duration.value())),
            period_ms=self._period.value(),
            phase_deg=self._phase.value(),
            periodic_offset=self._p_offset.value(),
            ramp_start=self._ramp_start.value(),
            ramp_end=self._ramp_end.value(),
            positive_coefficient=self._pos_coef.value(),
            negative_coefficient=self._neg_coef.value(),
            positive_saturation=self._pos_sat.value(),
            negative_saturation=self._neg_sat.value(),
            dead_band=self._dead_band.value(),
            center_offset_x=self._center.value(),
            center_offset_y=self._center.value(),
            apply_roll=self._chk_roll.isChecked(),
            apply_pitch=self._chk_pitch.isChecked(),
            use_envelope=self._chk_envelope.isChecked(),
            attack_level=self._atk_level.value(),
            attack_ms=self._atk_time.value(),
            fade_level=self._fade_level.value(),
            fade_ms=self._fade_time.value(),
        )

    def _update_group_enable(self) -> None:
        e = self._selected_effect()
        cond = e in (FfbEffect.SPRING, FfbEffect.DAMPER, FfbEffect.INERTIA, FfbEffect.FRICTION)
        per = e in (FfbEffect.SQUARE, FfbEffect.SINE, FfbEffect.TRIANGLE,
                    FfbEffect.SAWTOOTH_UP, FfbEffect.SAWTOOTH_DOWN)
        ramp = e is FfbEffect.RAMP_FORCE
        self._grp_periodic.set_body_enabled(per)
        self._grp_ramp.set_body_enabled(ramp)
        self._grp_condition.set_body_enabled(cond)
        self._grp_envelope.set_body_enabled(not cond)
        self._magnitude.set_enabled(not cond)
        self._direction.set_enabled(not cond)
        self._dir_pad.set_enabled(not cond)
        self._chk_infinite.setEnabled(not ramp)
        self._duration.set_enabled(not ramp and not self._chk_infinite.isChecked())

    def _invert_view_toggled(self, checked: bool) -> None:
        # display-only: negates the drawn arrows/position when checked
        self._invert = checked

    # ---------------------------------------------------------------- device

    def rescan_devices(self) -> None:
        self._cbo_device.clear()
        devices = self.dev.enumerate()
        for d in devices:
            self._cbo_device.addItem(d.product_name, d)
        if devices:
            self._status.setText(f"{len(devices)} FFB device(s)  |  log: {log.FilePath}")
        else:
            self._status.setText(f"no force-feedback devices found  |  log: {log.FilePath}")

    def connect_selected(self) -> None:
        data = self._cbo_device.currentData()
        if data is None:
            self._status.setText("pick a device first")
            return
        ok = self.dev.connect(data.guid_instance, int(self.winId()))
        if ok:
            self._status.setText(f"connected  |  axes: {self.dev.ffb_axes}")
            self._gain.set_value(self.dev.gain)
            self._apply_axis_availability()
            if self._chk_spring_on.isChecked():
                self.dev.apply_spring(self._spring_spec())
                self.dev.start_spring()
            if self._chk_effect_on.isChecked():
                self.dev.apply_main(self._main_spec())
                self.dev.start_main()
        else:
            self._status.setText(f"connect failed: {self.dev.last_error}")

    def _apply_axis_availability(self) -> None:
        pitch = self.dev.pitch_actuator
        self._chk_pitch.setEnabled(pitch)
        if not pitch:
            self._chk_pitch.setChecked(False)
        self._spring_offy.set_enabled(pitch)
        self._main_dirty = True
        self._spring_dirty = True

    def close_device(self) -> None:
        self.dev.disconnect()
        self._status.setText("device closed")

    # ---------------------------------------------------------------- tick

    def _tick(self) -> None:
        now = time.monotonic()
        dt = now - self._last_t
        self._last_t = now
        if dt <= 0 or dt > 0.5:
            dt = 1.0 / 60

        p = self.dev.poll()
        roll = p.roll if p.ok else self._last_roll
        pitch = p.pitch if p.ok else self._last_pitch

        vel_r = self._last_vel_r + 0.35 * ((roll - self._last_roll) / dt - self._last_vel_r)
        vel_p = self._last_vel_p + 0.35 * ((pitch - self._last_pitch) / dt - self._last_vel_p)
        acc_r = (vel_r - self._last_vel_r) / dt
        acc_p = (vel_p - self._last_vel_p) / dt
        self._last_roll, self._last_pitch = roll, pitch
        self._last_vel_r, self._last_vel_p = vel_r, vel_p

        spring_spec = self._spring_spec()
        main_spec = self._main_spec()
        self._dir_pad.set_readout(self._direction.value())

        try:
            if self._spring_dirty and self._chk_spring_on.isChecked():
                self.dev.apply_spring(spring_spec)
                self._spring_dirty = False
            if self._main_dirty and self._chk_effect_on.isChecked():
                self.dev.apply_main(main_spec)
                self._main_dirty = False
        except Exception as exc:
            self._show(str(exc))

        if (self._chk_effect_on.isChecked() and main_spec.duration_ms > 0
                and self._effect_started is not None
                and (now - self._effect_started) * 1000 > main_spec.duration_ms + 100):
            log.info(f"effect finished: {main_spec.duration_ms} ms - clearing checkbox")
            self._chk_effect_on.setChecked(False)

        t = (now - self._effect_started) if self._effect_started is not None else 0.0
        k = Kinematics(roll_pos=roll, pitch_pos=pitch, roll_vel=vel_r, pitch_vel=vel_p,
                       roll_acc=acc_r, pitch_acc=acc_p)
        f = ForceModel.evaluate_combined(
            spring_spec if self._chk_spring_on.isChecked() else None,
            main_spec if self._chk_effect_on.isChecked() else None, t, k)

        sign = -1.0 if getattr(self, "_invert", False) else 1.0
        self._view.set_state(
            sign * roll, sign * pitch, sign * f.fx, sign * f.fy,
            f.direction_deg if (self._chk_effect_on.isChecked() and not main_spec.is_condition)
            else float("nan"),
            self.dev.connected)

        self._frame += 1
        if self._frame % 6 == 0:
            self._debug.setPlainText(self._build_debug(main_spec, t, p, roll, pitch, vel_r, vel_p, f))

    def _build_debug(self, s: EffectSpec, t: float, p, roll: float, pitch: float,
                     vr: float, vp: float, f: ForceModel.Result) -> str:
        lines = [
            f"DEVICE  {self.dev.device_name}   conn={self.dev.connected}  ffb axes {self.dev.ffb_axes}",
            f"POS     roll X {p.raw_roll:7} ({roll:6.3f})   pitch Y {p.raw_pitch:7} ({pitch:6.3f})",
            f"        vel  r {vr:6.2f}  p {vp:6.2f} /s",
            "",
            f"SPRING  {'ON' if self.dev.spring_running else 'off'}   mag {self._spring_mag.value()}   "
            f"offX {self._spring_offx.value()}  offY {self._spring_offy.value()}",
            f"EFFECT  {'ON' if self.dev.main_running else 'off'}   {Pretty(s.effect)}",
        ]
        if not s.is_condition:
            lines.append(f"        dir {s.direction_deg:3} deg ({DirWord(s.direction_deg)})  mag {s.magnitude}  "
                         f"{'infinite' if s.duration_ms <= 0 else str(s.duration_ms) + 'ms'}  t={t:6.2f}s")
        if s.is_periodic:
            lines.append(f"        period {s.period_ms}ms  phase {s.phase_deg} deg  offset {s.periodic_offset}  "
                         f"wave {f.instantaneous:+6.3f}")
        if s.is_ramp:
            lines.append(f"        {s.ramp_start} -> {s.ramp_end}")
        if s.is_condition:
            lines.append(f"        coeff +{s.positive_coefficient}/-{s.negative_coefficient}  "
                         f"sat +{s.positive_saturation}/-{s.negative_saturation}  db {s.dead_band}  "
                         f"centre {s.center_offset_x}  axes {('X' if s.apply_roll else '-')}{('Y' if s.apply_pitch else '-')}")
        lines += [
            "",
            "COMMANDED FORCE  (tool model - spring + effect; compare to the real device)",
            f"        Fx {f.fx:+8.0f}  {'right' if f.fx > 0 else 'left' if f.fx < 0 else '-'}     "
            f"Fy {f.fy:+8.0f}  {'pull/nose-up' if f.fy > 0 else 'push/nose-down' if f.fy < 0 else '-'}",
            f"        |F| {f.magnitude:7.0f}     dir {f.direction_deg:6.1f} deg",
            "",
            f"gain {self._gain.value()}/10000",
            f"log  {log.FilePath}",
        ]
        return "\n".join(lines)

    def closeEvent(self, event) -> None:
        self._timer.stop()
        self.dev.disconnect()
        log.info("window closing")
        super().closeEvent(event)
````

- [ ] **Step 3: Create `directinput_ffb_tester/__main__.py`**

````python
"""Run the FFB test tool: python -m directinput_ffb_tester"""
from __future__ import annotations

import os
import sys

from PyQt6.QtWidgets import QApplication

from .window import MainWindow
from . import log


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("py_directinput_ffb FFB Test Tool")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
````

- [ ] **Step 4: Create `tests/test_window.py`**

````python
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import unittest
from PyQt6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])


class TestWindow(unittest.TestCase):
    def test_construct_smoke(self):
        from directinput_ffb_tester.window import MainWindow
        w = MainWindow()
        self.assertIn("FFB device", w._status.text())
        w.close()


if __name__ == "__main__":
    unittest.main()
````

- [ ] **Step 5: Run and verify it passes (offscreen)**

Run: `python -m unittest tests.test_window -v`
Expected: 1 test PASS. Also importable: `python -c "import directinput_ffb_tester.window"`.

---

### Task 9: Launcher, README/AGENTS updates, final verification

**Files:**
- Create: `directinput_ffb_test_tool.py`
- Modify: `README.md` (new "FFB Test Tool" section + requirements), `AGENTS.md` (commands + architecture note)

**Interfaces:**
- Consumes: all tasks.
- Produces: root launcher `python directinput_ffb_test_tool.py`.

- [ ] **Step 1: Create root launcher**

````python
"""Launcher for the PyQt6 FFB test tool (port of barsk/FFBTestTool).

Run from the repo root:  python directinput_ffb_test_tool.py
"""
from directinput_ffb_tester.__main__ import main
import sys

sys.exit(main())
````

- [ ] **Step 2: README/AGENTS updates**

README: add to Requirements: `pip install PyQt6` only for the tester; add `python directinput_ffb_test_tool.py` to the Demo section; add a short feature note (visualisation, spring safeguard, live sliders).
AGENTS.md: add `python directinput_ffb_test_tool.py` under Run, note the `directinput_ffb_tester/` package (spec/device/views/window/log) is the FFBTestTool port, and note its unit tests live in `tests/` and run with `python -m unittest discover -s tests -v`.

- [ ] **Step 3: Full verification**

Run all of the following from the repo root:
1. `python -m py_compile directinput_ffb/*.py directinput_ffb_tester/*.py directinput_ffb_test_tool.py`
2. `python -m unittest discover -s tests -v`
3. `python -c "import directinput_ffb; import directinput_ffb_tester; from directinput_ffb_tester.spec import ForceModel; from directinput_ffb_tester.device import DeviceSession"`
4. `python main.py` �� still prints "No attached force-feedback game controllers found."
5. `python directinput_ffb_test_tool.py` with `QT_QPA_PLATFORM=offscreen`? (interactive app �� skip; rely on Step 2 tests)

Expected: all PASS; the existing GUI tester and main.py still run unchanged.

- [ ] **Step 4: Manual hardware checklist (user)**
- Connect wheel/yoke: spring ON by default, centring force felt.
- Pick Constant 270 deg: wheel rolls right; check compass + arrows.
- Live slider updates while running; envelope attack/fade felt; device gain works.
- 1-axis device: pitch controls greyed out.

---
