"""Device session: connect, poll, and two effect slots (background spring + main)."""
from __future__ import annotations

from dataclasses import dataclass

from directinput_ffb import (
    create_direct_input,
    enum_devices,
    create_device,
    set_cooperative_level,
    set_data_format,
    acquire,
    unacquire,
    enum_ffb_axes_actuator_offsets,
    set_axis_range,
    get_axis_range,
    get_device_gain,
    set_device_gain,
    set_autocenter,
    stop_all_effects,
    create_constant_force_effect,
    create_ramp_force_effect,
    create_square_effect,
    create_sine_effect,
    create_triangle_effect,
    create_sawtooth_up_effect,
    create_sawtooth_down_effect,
    create_spring_effect,
    create_damper_effect,
    create_inertia_effect,
    create_friction_effect,
)
from directinput_ffb.dinput_api import build_joystick_data_format
from directinput_ffb.dinput_definitions import (
    DIJOFS_X,
    DIJOFS_Y,
    DIEFF_CARTESIAN,
    DIEFF_POLAR,
    C,
    DIJOYSTATE,
    DICONDITION,
    DIDEVICEINSTANCEW,
)
from directinput_ffb.dinput_effects import EffectHandle

from . import log
from .spec import FfbEffect, EffectSpec

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
    return axes


def normalize(raw: int, lo: int, hi: int) -> float:
    """Map a raw value onto -1..1 using the axis' actual range.

    Handles device ranges that are not zero-centred (e.g. 0..65535 with the
    centre at 32767), which is common for HID PID devices, and the symmetric
    +/-10000 ranges this tool requests.
    """
    span = hi - lo
    if span <= 0:
        return 0.0
    return ((raw - lo) / span) * 2.0 - 1.0


@dataclass
class PollResult:
    ok: bool
    raw_roll: int
    raw_pitch: int
    roll: float
    pitch: float
    buttons: int = 0


class _Slot:
    def __init__(self, name: str) -> None:
        self.name = name
        self.fx: EffectHandle | None = None
        self.running = False
        self.last_type: FfbEffect | None = None
        self.last_axes: tuple[int, ...] = ()
        self.last_spec: EffectSpec | None = None

    def dispose(self) -> None:
        if self.fx is not None:
            try:
                self.fx.unload()
            except Exception as exc:
                log.warn(f"[{self.name}] unload failed: {exc}")
            self.fx = None
            self.last_type = None
            self.last_axes = ()
            self.last_spec = None
            self.running = False


class DeviceSession:
    def __init__(self) -> None:
        self._di = None
        self._device = None
        self._hwnd = None
        self._data_format = None
        self.ffb_axes: list[int] = [DIJOFS_X, DIJOFS_Y]
        self._axis_ranges: dict[int, tuple[int, int]] = {}
        self._main = _Slot("main")
        self._spring = _Slot("spring")
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

            self._data_format = set_data_format(
                self._device, build_joystick_data_format(tuple(axis_subset)))

            # Normalise the logical range to +/-AXIS_RANGE (best effort - some
            # HID PID devices refuse DIPROP_RANGE), then remember whatever range
            # the device actually has so poll() can normalise in software.
            self._axis_ranges = {}
            for axis in axis_subset:
                try:
                    set_axis_range(self._device, axis, -AXIS_RANGE, AXIS_RANGE)
                except Exception as exc:
                    log.warn(f"axis range failed for {axis}: {exc}")
                try:
                    lo, hi = get_axis_range(self._device, axis)
                    self._axis_ranges[axis] = (int(lo), int(hi))
                except Exception:
                    self._axis_ranges[axis] = (-AXIS_RANGE, AXIS_RANGE)

            try:
                set_autocenter(self._device, False)
            except Exception as exc:
                log.warn(f"disable autocenter failed: {exc}")
            acquire(self._device)
            try:
                stop_all_effects(self._device)
            except Exception as exc:
                log.warn(f"stop-all failed: {exc}")
            try:
                self.gain = get_device_gain(self._device)
            except Exception:
                pass
            try:
                info = DIDEVICEINSTANCEW()
                info.dwSize = C.sizeof(DIDEVICEINSTANCEW)
                self._device.GetDeviceInfo(info)
                self.device_name = info.tszInstanceName
            except Exception:
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
            raw_roll = int(state.lX)
            raw_pitch = int(state.lY)
            buttons = 0
            for i, b in enumerate(state.rgbButtons[:32]):
                if b:
                    buttons |= 1 << i
            roll_lo, roll_hi = self._axis_ranges.get(DIJOFS_X, (-AXIS_RANGE, AXIS_RANGE))
            pitch_lo, pitch_hi = self._axis_ranges.get(DIJOFS_Y, (-AXIS_RANGE, AXIS_RANGE))
            return PollResult(True, raw_roll, raw_pitch,
                              normalize(raw_roll, roll_lo, roll_hi),
                              normalize(raw_pitch, pitch_lo, pitch_hi),
                              buttons)
        except Exception as exc:
            self.last_error = f"poll: {exc}"
            try:
                acquire(self._device)
            except Exception:
                pass
            return PollResult(False, 0, 0, 0.0, 0.0)

    # ---- slots -----------------------------------------------------------

    def _effects_axes(self, spec: EffectSpec) -> list[int]:
        if spec.is_condition:
            return select_condition_axes(
                spec.apply_roll, spec.apply_pitch, self.roll_actuator,
                self.pitch_actuator, self.ffb_axes)
        return list(self.ffb_axes)

    def _build_kwargs(self, spec: EffectSpec):
        axes_offsets = self._effects_axes(spec)
        if not axes_offsets:
            raise ValueError("No available force-feedback axis is selected.")
        kwargs = dict(axes_offsets=tuple(axes_offsets))
        if spec.is_condition:
            kwargs["direction_basis"] = DIEFF_POLAR
            kwargs["direction_hundredths_deg"] = 0
            kwargs["per_axis"] = [
                dict(offset=(spec.center_offset_x if axis == DIJOFS_X
                             else spec.center_offset_y),
                     positive_coefficient=spec.positive_coefficient,
                     negative_coefficient=spec.negative_coefficient,
                     positive_saturation=spec.positive_saturation,
                     negative_saturation=spec.negative_saturation,
                     dead_band=spec.dead_band)
                for axis in axes_offsets
            ]
        else:
            kwargs["direction_basis"] = DIEFF_CARTESIAN
            kwargs["direction_hundredths_deg"] = spec.direction_deg * 100
            kwargs["duration_us"] = (spec.duration_ms * 1000) if spec.duration_ms > 0 else 0xFFFFFFFF
            if spec.effect == FfbEffect.RAMP_FORCE:
                kwargs["start_magnitude"] = spec.ramp_start
                kwargs["end_magnitude"] = spec.ramp_end
            else:
                kwargs["magnitude"] = spec.magnitude
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
            raise RuntimeError("not connected")
        try:
            axes_offsets = self._effects_axes(spec)
            if not axes_offsets:
                slot.dispose()
                raise ValueError("No available force-feedback axis is selected.")
            if (slot.fx is None or slot.last_type != spec.effect
                    or slot.last_axes != tuple(axes_offsets)):
                was_running = slot.running
                slot.dispose()
                factory = EFFECT_GUID_FACTORY[spec.effect]
                slot.fx = factory(self._device, **self._build_kwargs(spec))
                slot.last_type = spec.effect
                slot.last_axes = tuple(axes_offsets)
                slot.last_spec = spec.clone()
                slot.running = was_running
                if was_running:
                    self._start(slot)
                return
            old = slot.last_spec
            update = {"start": slot.running}
            if not spec.is_condition:
                if old is None or old.duration_ms != spec.duration_ms:
                    update["duration_ms"] = spec.duration_ms
                if old is None or old.direction_deg != spec.direction_deg:
                    update["direction_hundredths_deg"] = spec.direction_deg * 100
                envelope_changed = old is None or any((
                    old.use_envelope != spec.use_envelope,
                    old.attack_level != spec.attack_level,
                    old.attack_ms != spec.attack_ms,
                    old.fade_level != spec.fade_level,
                    old.fade_ms != spec.fade_ms,
                ))
                if envelope_changed:
                    update["envelope"] = self._live_envelope(spec)
            update["type_specific"] = (
                self._live_condition_array(spec) if spec.is_condition
                else self._live_type_specific(spec)
            )
            try:
                slot.fx.apply(**update)
                slot.last_spec = spec.clone()
            except Exception as update_exc:
                # Some drivers expose an effect but do not support all of its
                # parameters dynamically. Recreate it with the complete static
                # description instead of leaving the UI and device out of sync.
                log.warn(f"[{slot.name}] dynamic update failed; recreating: {update_exc}")
                was_running = slot.running
                slot.dispose()
                factory = EFFECT_GUID_FACTORY[spec.effect]
                slot.fx = factory(self._device, **self._build_kwargs(spec))
                slot.last_type = spec.effect
                slot.last_axes = tuple(axes_offsets)
                slot.last_spec = spec.clone()
                if was_running:
                    self._start(slot)
        except Exception as exc:
            self.last_error = f"{slot.name}: {exc}"
            log.error(f"{slot.name} apply", exc)
            raise

    def _live_condition_array(self, spec: EffectSpec):
        axes_offsets = self._effects_axes(spec)
        array_type = DICONDITION * len(axes_offsets)
        conditions = array_type()
        for i, axis in enumerate(axes_offsets):
            conditions[i].lOffset = (spec.center_offset_x if axis == DIJOFS_X
                                     else spec.center_offset_y)
            conditions[i].lPositiveCoefficient = spec.positive_coefficient
            conditions[i].lNegativeCoefficient = spec.negative_coefficient
            conditions[i].dwPositiveSaturation = spec.positive_saturation
            conditions[i].dwNegativeSaturation = spec.negative_saturation
            conditions[i].lDeadBand = spec.dead_band
        return conditions

    def _live_envelope(self, spec: EffectSpec):
        if not spec.use_envelope:
            return None
        from directinput_ffb.dinput_definitions import DIENVELOPE
        env = DIENVELOPE()
        env.dwSize = C.sizeof(DIENVELOPE)
        env.dwAttackLevel = spec.attack_level
        env.dwAttackTime = spec.attack_ms * 1000
        env.dwFadeLevel = spec.fade_level
        env.dwFadeTime = spec.fade_ms * 1000
        return env

    def _live_type_specific(self, spec: EffectSpec):
        from directinput_ffb.dinput_definitions import (
            DICONSTANTFORCE,
            DIRAMPFORCE,
            DIPERIODIC,
        )
        if spec.effect == FfbEffect.CONSTANT_FORCE:
            return DICONSTANTFORCE(lMagnitude=spec.magnitude)
        if spec.effect == FfbEffect.RAMP_FORCE:
            return DIRAMPFORCE(lStart=spec.ramp_start, lEnd=spec.ramp_end)
        if spec.magnitude < 0 or abs(spec.periodic_offset) + spec.magnitude > 10000:
            raise ValueError(
                "Periodic effects require magnitude >= 0 and "
                "abs(offset) + magnitude <= 10000."
            )
        return DIPERIODIC(
            dwMagnitude=spec.magnitude,
            lOffset=spec.periodic_offset,
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
            raise

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
