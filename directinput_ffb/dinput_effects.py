"""Effect creation and lifetime helpers for DirectInput force feedback.

This module extends the original constant-force-only wrapper so it can create
all standard DirectInput force-feedback effect families:

- constant force
- ramp force
- periodic forces: square, sine, triangle, sawtooth-up, sawtooth-down
- condition forces: spring, damper, inertia, friction

The important implementation detail is lifetime management. DirectInput stores
native pointers to the arrays and structures provided in ``DIEFFECT``.
Python code therefore must keep those objects alive for as long as the effect
may access them.
"""

from __future__ import annotations

import math

from dataclasses import dataclass
from typing import Iterable, Sequence

from .dinput_types import C, GUID, LPVOID, POINTER
from .dinput_definitions import (
    DWORD,
    LONG,
    DICONSTANTFORCE,
    DIRAMPFORCE,
    DIPERIODIC,
    DICONDITION,
    DIEFFECT,
    IDirectInputDevice8W,
    IDirectInputEffect,
    GUID_ConstantForce,
    GUID_RampForce,
    GUID_Square,
    GUID_Sine,
    GUID_Triangle,
    GUID_SawtoothUp,
    GUID_SawtoothDown,
    GUID_Spring,
    GUID_Damper,
    GUID_Inertia,
    GUID_Friction,
    DIJOFS_X,
    DIJOFS_Y,
    DI_FFNOMINALMAX,
    DIEB_NOTRIGGER,
    DIEFF_OBJECTOFFSETS,
    DIEFF_POLAR,
    DIEFF_CARTESIAN,
    DIEP_TYPESPECIFICPARAMS,
    DIEP_START,
)
from .dinput_api import check_hr


@dataclass
class EffectHandle:
    """Wrapper around one ``IDirectInputEffect`` instance.

    ``type_specific`` stores the payload pointed to by
    ``DIEFFECT.lpvTypeSpecificParams``. For condition effects, this may be a
    single ``DICONDITION`` or an array of them. ``keepalive`` stores any other
    Python-owned objects whose addresses are exposed to native code.
    """

    effect: POINTER(IDirectInputEffect)
    dieffect: DIEFFECT
    axes: object
    directions: object
    type_specific: object
    keepalive: tuple[object, ...] = ()

    def start(self, iterations: int = 1, flags: int = 0) -> None:
        hr = self.effect.Start(iterations, flags)
        check_hr(hr, "IDirectInputEffect.Start")

    def stop(self) -> None:
        hr = self.effect.Stop()
        check_hr(hr, "IDirectInputEffect.Stop")

    def download(self) -> None:
        hr = self.effect.Download()
        check_hr(hr, "IDirectInputEffect.Download")

    def unload(self) -> None:
        hr = self.effect.Unload()
        check_hr(hr, "IDirectInputEffect.Unload")

    def set_type_specific_params(self, *, start: bool = False) -> None:
        """Push the current type-specific payload into the native effect.

        This is the common update path for constant, ramp, periodic, and
        condition effects when only their type-specific structure changes.
        """

        flags = DIEP_TYPESPECIFICPARAMS
        if start:
            flags |= DIEP_START
        hr = self.effect.SetParameters(C.byref(self.dieffect), flags)
        check_hr(hr, "IDirectInputEffect.SetParameters")


class ConstantForceEffectHandle(EffectHandle):
    """Specialized helper for constant-force effects."""

    @property
    def force(self) -> DICONSTANTFORCE:
        return self.type_specific

    def set_magnitude(self, magnitude: int, *, start: bool = False) -> None:
        self.force.lMagnitude = magnitude
        self.set_type_specific_params(start=start)


class RampForceEffectHandle(EffectHandle):
    """Specialized helper for ramp-force effects."""

    @property
    def force(self) -> DIRAMPFORCE:
        return self.type_specific

    def set_ramp(self, start_magnitude: int, end_magnitude: int, *, start: bool = False) -> None:
        self.force.lStart = start_magnitude
        self.force.lEnd = end_magnitude
        self.set_type_specific_params(start=start)


class PeriodicEffectHandle(EffectHandle):
    """Specialized helper for periodic effects."""

    @property
    def periodic(self) -> DIPERIODIC:
        return self.type_specific

    def set_periodic(
        self,
        *,
        magnitude: int | None = None,
        offset: int | None = None,
        phase_hundredths_deg: int | None = None,
        period_us: int | None = None,
        start: bool = False,
    ) -> None:
        if magnitude is not None:
            self.periodic.dwMagnitude = magnitude
        if offset is not None:
            self.periodic.lOffset = offset
        if phase_hundredths_deg is not None:
            self.periodic.dwPhase = phase_hundredths_deg
        if period_us is not None:
            self.periodic.dwPeriod = period_us
        self.set_type_specific_params(start=start)


class ConditionEffectHandle(EffectHandle):
    """Specialized helper for condition effects."""

    @property
    def conditions(self):
        return self.type_specific

    def set_condition(
        self,
        index: int,
        *,
        offset: int | None = None,
        positive_coefficient: int | None = None,
        negative_coefficient: int | None = None,
        positive_saturation: int | None = None,
        negative_saturation: int | None = None,
        dead_band: int | None = None,
        start: bool = False,
    ) -> None:
        condition = self.conditions[index]
        if offset is not None:
            condition.lOffset = offset
        if positive_coefficient is not None:
            condition.lPositiveCoefficient = positive_coefficient
        if negative_coefficient is not None:
            condition.lNegativeCoefficient = negative_coefficient
        if positive_saturation is not None:
            condition.dwPositiveSaturation = positive_saturation
        if negative_saturation is not None:
            condition.dwNegativeSaturation = negative_saturation
        if dead_band is not None:
            condition.lDeadBand = dead_band
        self.set_type_specific_params(start=start)


def angle_deg_to_cartesian(angle_deg: float, scale: int = 32767) -> tuple[int, int]:
    radians = math.radians(angle_deg)
    x = int(round(math.sin(radians) * scale))
    y = int(round(-math.cos(radians) * scale))
    return x, y


def _build_axes_and_directions(
    axes_offsets: Sequence[int],
    direction_hundredths_deg: int,
    direction_basis: int
) -> tuple[int, object, object]:
    """Allocate the axis and direction arrays used by ``DIEFFECT``.

    The helper keeps the old behaviour from the working script: one-axis and
    two-axis effects are supported directly, and two-axis effects use polar
    coordinates where the second direction entry is reserved and must be zero.
    """

    axis_count = len(axes_offsets)
    if axis_count not in (1, 2):
        raise ValueError("This helper supports only 1-axis or 2-axis effects.")

    axes = (DWORD * axis_count)(*axes_offsets)
    if axis_count == 1:
        directions = (LONG * 1)(0)
    else:
        directions = (LONG * 2)(direction_hundredths_deg, 0)
        if direction_basis == DIEFF_CARTESIAN:
            directions = (LONG * 2)(*angle_deg_to_cartesian(direction_hundredths_deg / 100))

    return axis_count, axes, directions


def _build_effect_description(
    *,
    axes_offsets: Sequence[int],
    direction_hundredths_deg: int,
    direction_basis: int,
    duration_us: int,
    type_specific: object,
    gain: int = DI_FFNOMINALMAX,
) -> tuple[DIEFFECT, object, object]:
    """Create the common ``DIEFFECT`` structure for the standard effect helpers."""

    axis_count, axes, directions = _build_axes_and_directions(axes_offsets, direction_hundredths_deg, direction_basis)

    effect_desc = DIEFFECT()
    effect_desc.dwSize = C.sizeof(DIEFFECT)
    effect_desc.dwFlags = DIEFF_OBJECTOFFSETS | direction_basis
    effect_desc.dwDuration = duration_us
    effect_desc.dwSamplePeriod = 0
    effect_desc.dwGain = gain
    effect_desc.dwTriggerButton = DIEB_NOTRIGGER
    effect_desc.dwTriggerRepeatInterval = 0
    effect_desc.cAxes = axis_count
    effect_desc.rgdwAxes = C.cast(axes, POINTER(DWORD))
    effect_desc.rglDirection = C.cast(directions, POINTER(LONG))
    effect_desc.lpEnvelope = None
    effect_desc.cbTypeSpecificParams = C.sizeof(type_specific)
    effect_desc.lpvTypeSpecificParams = C.cast(C.pointer(type_specific), LPVOID)
    effect_desc.dwStartDelay = 0
    return effect_desc, axes, directions


def _build_condition_description(
    *,
    axes_offsets: Sequence[int],
    direction_hundredths_deg: int,
    direction_basis: int,
    duration_us: int,
    conditions: object,
    gain: int = DI_FFNOMINALMAX,
) -> tuple[DIEFFECT, object, object]:
    """Build a ``DIEFFECT`` description for condition effects.

    ``conditions`` is expected to be a ctypes array of ``DICONDITION``.
    Unlike the single-structure force helpers, ``cbTypeSpecificParams`` must be
    the total byte count of the whole array.
    """

    axis_count, axes, directions = _build_axes_and_directions(axes_offsets, direction_hundredths_deg, direction_basis)

    effect_desc = DIEFFECT()
    effect_desc.dwSize = C.sizeof(DIEFFECT)
    effect_desc.dwFlags = DIEFF_OBJECTOFFSETS | direction_basis
    effect_desc.dwDuration = duration_us
    effect_desc.dwSamplePeriod = 0
    effect_desc.dwGain = gain
    effect_desc.dwTriggerButton = DIEB_NOTRIGGER
    effect_desc.dwTriggerRepeatInterval = 0
    effect_desc.cAxes = axis_count
    effect_desc.rgdwAxes = C.cast(axes, POINTER(DWORD))
    effect_desc.rglDirection = C.cast(directions, POINTER(LONG))
    effect_desc.lpEnvelope = None
    effect_desc.cbTypeSpecificParams = C.sizeof(conditions)
    effect_desc.lpvTypeSpecificParams = C.cast(conditions, LPVOID)
    effect_desc.dwStartDelay = 0
    return effect_desc, axes, directions


def _create_effect(
    device: POINTER(IDirectInputDevice8W),
    *,
    effect_guid: GUID,
    effect_desc: DIEFFECT,
    handle_cls: type[EffectHandle] = EffectHandle,
    type_specific: object,
    axes: object,
    directions: object,
    keepalive: tuple[object, ...] = (),
) -> EffectHandle:
    """Call ``CreateEffect`` and wrap the returned COM object."""

    effect = device.CreateEffect(C.byref(effect_guid), C.byref(effect_desc), None)
    return handle_cls(
        effect=effect,
        dieffect=effect_desc,
        axes=axes,
        directions=directions,
        type_specific=type_specific,
        keepalive=keepalive,
    )


def create_constant_force_effect(
    device: POINTER(IDirectInputDevice8W),
    *,
    magnitude: int = 5000,
    direction_hundredths_deg: int = 0,
    direction_basis: int = DIEFF_POLAR,
    duration_us: int = 1_000_000,
    axes_offsets: tuple[int, ...] = (DIJOFS_X, DIJOFS_Y),
) -> ConstantForceEffectHandle:
    """Create a standard constant-force effect."""

    force = DICONSTANTFORCE(lMagnitude=magnitude)
    effect_desc, axes, directions = _build_effect_description(
        axes_offsets=axes_offsets,
        direction_hundredths_deg=direction_hundredths_deg,
        direction_basis=direction_basis,
        duration_us=duration_us,
        type_specific=force,
    )
    print("*" * 10, directions[0], directions[1])
    return _create_effect(
        device,
        effect_guid=GUID_ConstantForce,
        effect_desc=effect_desc,
        handle_cls=ConstantForceEffectHandle,
        type_specific=force,
        axes=axes,
        directions=directions,
    )


def create_ramp_force_effect(
    device: POINTER(IDirectInputDevice8W),
    *,
    start_magnitude: int = 0,
    end_magnitude: int = 5000,
    direction_hundredths_deg: int = 0,
    direction_basis: int = DIEFF_POLAR,
    duration_us: int = 1_000_000,
    axes_offsets: tuple[int, ...] = (DIJOFS_X, DIJOFS_Y),
) -> RampForceEffectHandle:
    """Create a standard ramp-force effect."""

    force = DIRAMPFORCE(lStart=start_magnitude, lEnd=end_magnitude)
    effect_desc, axes, directions = _build_effect_description(
        axes_offsets=axes_offsets,
        direction_hundredths_deg=direction_hundredths_deg,
        direction_basis=direction_basis,
        duration_us=duration_us,
        type_specific=force,
    )
    return _create_effect(
        device,
        effect_guid=GUID_RampForce,
        effect_desc=effect_desc,
        handle_cls=RampForceEffectHandle,
        type_specific=force,
        axes=axes,
        directions=directions,
    )


def create_periodic_effect(
    device: POINTER(IDirectInputDevice8W),
    *,
    effect_guid: GUID,
    magnitude: int = 5000,
    offset: int = 0,
    phase_hundredths_deg: int = 0,
    period_us: int = 500_000,
    direction_hundredths_deg: int = 0,
    direction_basis: int = DIEFF_POLAR,
    duration_us: int = 1_000_000,
    axes_offsets: tuple[int, ...] = (DIJOFS_X, DIJOFS_Y),
) -> PeriodicEffectHandle:
    """Create a periodic effect given one of the standard periodic GUIDs."""

    periodic = DIPERIODIC(
        dwMagnitude=magnitude,
        lOffset=offset,
        dwPhase=phase_hundredths_deg,
        dwPeriod=period_us,
    )
    effect_desc, axes, directions = _build_effect_description(
        axes_offsets=axes_offsets,
        direction_hundredths_deg=direction_hundredths_deg,
        direction_basis=direction_basis,
        duration_us=duration_us,
        type_specific=periodic,
    )
    return _create_effect(
        device,
        effect_guid=effect_guid,
        effect_desc=effect_desc,
        handle_cls=PeriodicEffectHandle,
        type_specific=periodic,
        axes=axes,
        directions=directions,
    )


def create_square_effect(device: POINTER(IDirectInputDevice8W), **kwargs) -> PeriodicEffectHandle:
    return create_periodic_effect(device, effect_guid=GUID_Square, **kwargs)


def create_sine_effect(device: POINTER(IDirectInputDevice8W), **kwargs) -> PeriodicEffectHandle:
    return create_periodic_effect(device, effect_guid=GUID_Sine, **kwargs)


def create_triangle_effect(device: POINTER(IDirectInputDevice8W), **kwargs) -> PeriodicEffectHandle:
    return create_periodic_effect(device, effect_guid=GUID_Triangle, **kwargs)


def create_sawtooth_up_effect(device: POINTER(IDirectInputDevice8W), **kwargs) -> PeriodicEffectHandle:
    return create_periodic_effect(device, effect_guid=GUID_SawtoothUp, **kwargs)


def create_sawtooth_down_effect(device: POINTER(IDirectInputDevice8W), **kwargs) -> PeriodicEffectHandle:
    return create_periodic_effect(device, effect_guid=GUID_SawtoothDown, **kwargs)


def _make_condition_array(
    *,
    axis_count: int,
    positive_coefficient: int,
    negative_coefficient: int | None,
    positive_saturation: int,
    negative_saturation: int | None,
    dead_band: int,
    offset: int,
    per_axis: Iterable[dict[str, int]] | None,
) -> object:
    """Create the ``DICONDITION`` array used by spring/damper/inertia/friction.

    If ``per_axis`` is omitted, the same condition is copied to all axes. This
    is the most convenient default for two-axis devices.
    """

    if negative_coefficient is None:
        negative_coefficient = positive_coefficient
    if negative_saturation is None:
        negative_saturation = positive_saturation

    array_type = DICONDITION * axis_count
    conditions = array_type()

    if per_axis is None:
        per_axis = [{} for _ in range(axis_count)]

    per_axis_list = list(per_axis)
    if len(per_axis_list) != axis_count:
        raise ValueError("per_axis must have exactly one entry per axis.")

    for index, overrides in enumerate(per_axis_list):
        conditions[index].lOffset = overrides.get("offset", offset)
        conditions[index].lPositiveCoefficient = overrides.get("positive_coefficient", positive_coefficient)
        conditions[index].lNegativeCoefficient = overrides.get("negative_coefficient", negative_coefficient)
        conditions[index].dwPositiveSaturation = overrides.get("positive_saturation", positive_saturation)
        conditions[index].dwNegativeSaturation = overrides.get("negative_saturation", negative_saturation)
        conditions[index].lDeadBand = overrides.get("dead_band", dead_band)

    return conditions


def create_condition_effect(
    device: POINTER(IDirectInputDevice8W),
    *,
    effect_guid: GUID,
    positive_coefficient: int = 5000,
    negative_coefficient: int | None = None,
    positive_saturation: int = 10000,
    negative_saturation: int | None = None,
    dead_band: int = 0,
    offset: int = 0,
    direction_hundredths_deg: int = 0,
    direction_basis: int = DIEFF_POLAR,
    duration_us: int = 0xFFFFFFFF,
    axes_offsets: tuple[int, ...] = (DIJOFS_X, DIJOFS_Y),
    per_axis: Iterable[dict[str, int]] | None = None,
) -> ConditionEffectHandle:
    """Create a condition effect using one of the standard condition GUIDs.

    ``per_axis`` allows axis-specific overrides when you want different spring,
    damper, inertia, or friction values on each axis.
    """

    axis_count = len(axes_offsets)
    if axis_count not in (1, 2):
        raise ValueError("This helper supports only 1-axis or 2-axis effects.")

    conditions = _make_condition_array(
        axis_count=axis_count,
        positive_coefficient=positive_coefficient,
        negative_coefficient=negative_coefficient,
        positive_saturation=positive_saturation,
        negative_saturation=negative_saturation,
        dead_band=dead_band,
        offset=offset,
        per_axis=per_axis,
    )

    effect_desc, axes, directions = _build_condition_description(
        axes_offsets=axes_offsets,
        direction_hundredths_deg=direction_hundredths_deg,
        direction_basis=direction_basis,
        duration_us=duration_us,
        conditions=conditions,
    )
    return _create_effect(
        device,
        effect_guid=effect_guid,
        effect_desc=effect_desc,
        handle_cls=ConditionEffectHandle,
        type_specific=conditions,
        axes=axes,
        directions=directions,
    )


def create_spring_effect(device: POINTER(IDirectInputDevice8W), **kwargs) -> ConditionEffectHandle:
    return create_condition_effect(device, effect_guid=GUID_Spring, **kwargs)


def create_damper_effect(device: POINTER(IDirectInputDevice8W), **kwargs) -> ConditionEffectHandle:
    return create_condition_effect(device, effect_guid=GUID_Damper, **kwargs)


def create_inertia_effect(device: POINTER(IDirectInputDevice8W), **kwargs) -> ConditionEffectHandle:
    return create_condition_effect(device, effect_guid=GUID_Inertia, **kwargs)


def create_friction_effect(device: POINTER(IDirectInputDevice8W), **kwargs) -> ConditionEffectHandle:
    return create_condition_effect(device, effect_guid=GUID_Friction, **kwargs)


__all__ = [
    "EffectHandle",
    "ConstantForceEffectHandle",
    "RampForceEffectHandle",
    "PeriodicEffectHandle",
    "ConditionEffectHandle",
    "create_constant_force_effect",
    "create_ramp_force_effect",
    "create_periodic_effect",
    "create_square_effect",
    "create_sine_effect",
    "create_triangle_effect",
    "create_sawtooth_up_effect",
    "create_sawtooth_down_effect",
    "create_condition_effect",
    "create_spring_effect",
    "create_damper_effect",
    "create_inertia_effect",
    "create_friction_effect",
    "angle_deg_to_cartesian",
]
