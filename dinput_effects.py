"""Effect creation and lifetime helpers for DirectInput force feedback."""

from __future__ import annotations

from dataclasses import dataclass

from dinput_types import C, LPVOID, POINTER
from dinput_definitions import (
    DWORD,
    LONG,
    DICONSTANTFORCE,
    DIEFFECT,
    IDirectInputDevice8W,
    IDirectInputEffect,
    GUID_ConstantForce,
    DIJOFS_X,
    DIJOFS_Y,
    DI_FFNOMINALMAX,
    DIEB_NOTRIGGER,
    DIEFF_OBJECTOFFSETS,
    DIEFF_POLAR,
    DIEP_TYPESPECIFICPARAMS,
    DIEP_START,
)
from dinput_api import check_hr


@dataclass
class ConstantForceEffectHandle:
    """Python wrapper around one ``IDirectInputEffect`` instance.

    Why this wrapper exists
    -----------------------
    DirectInput stores pointers to arrays and structures supplied in the
    ``DIEFFECT`` description. In C++, those objects would usually live on the
    stack or in a class member with obvious lifetime. In Python, we must keep
    explicit references alive so the garbage collector does not reclaim memory
    still reachable from native code.

    The wrapper therefore owns:
    - the COM effect interface itself
    - the ``DIEFFECT`` structure used to create/update it
    - the axis and direction arrays
    - the ``DICONSTANTFORCE`` type-specific payload
    """

    effect: POINTER(IDirectInputEffect)
    dieffect: DIEFFECT
    axes: object
    directions: object
    force: DICONSTANTFORCE

    def start(self, iterations: int = 1, flags: int = 0) -> None:
        """Start playback of the effect."""

        hr = self.effect.Start(iterations, flags)
        check_hr(hr, "IDirectInputEffect.Start")

    def stop(self) -> None:
        """Stop playback of the effect."""

        hr = self.effect.Stop()
        check_hr(hr, "IDirectInputEffect.Stop")

    def download(self) -> None:
        """Explicitly download the effect to the device, if supported."""

        hr = self.effect.Download()
        check_hr(hr, "IDirectInputEffect.Download")

    def unload(self) -> None:
        """Unload the effect from the device."""

        hr = self.effect.Unload()
        check_hr(hr, "IDirectInputEffect.Unload")

    def set_magnitude(self, magnitude: int, *, start: bool = False) -> None:
        """Update only the constant-force magnitude in-place.

        This is the most common runtime tweak for a constant-force effect.
        Because the rest of the ``DIEFFECT`` description stays unchanged, we can
        call ``SetParameters`` with only ``DIEP_TYPESPECIFICPARAMS``.
        """

        self.force.lMagnitude = magnitude
        flags = DIEP_TYPESPECIFICPARAMS
        if start:
            flags |= DIEP_START
        hr = self.effect.SetParameters(C.byref(self.dieffect), flags)
        check_hr(hr, "IDirectInputEffect.SetParameters")


def create_constant_force_effect(
    device: POINTER(IDirectInputDevice8W),
    *,
    magnitude: int = 5000,
    direction_hundredths_deg: int = 0,
    duration_us: int = 1_000_000,
    axes_offsets: tuple[int, ...] = (DIJOFS_X, DIJOFS_Y),
) -> ConstantForceEffectHandle:
    """Create a constant-force effect object on a DirectInput device.

    Parameters
    ----------
    magnitude:
        Signed constant force value. DirectInput commonly uses a nominal range
        around ``-10000`` to ``10000``.
    direction_hundredths_deg:
        Polar direction expressed in hundredths of a degree. ``18000`` means
        ``180.00`` degrees.
    duration_us:
        Duration in microseconds. This matches DirectInput's native unit.
    axes_offsets:
        The data-format offsets of the axes that define the force direction.

    Notes
    -----
    For a two-axis polar effect, the second direction entry is reserved and must
    be zero. This mirrors the pattern used in the original working script.
    """

    axis_count = len(axes_offsets)
    if axis_count not in (1, 2):
        raise ValueError("This helper supports only 1-axis or 2-axis effects.")

    axes = (DWORD * axis_count)(*axes_offsets)
    if axis_count == 1:
        directions = (LONG * 1)(direction_hundredths_deg)
    else:
        directions = (LONG * 2)(direction_hundredths_deg, 0)

    force = DICONSTANTFORCE()
    force.lMagnitude = magnitude

    effect_desc = DIEFFECT()
    effect_desc.dwSize = C.sizeof(DIEFFECT)
    effect_desc.dwFlags = DIEFF_OBJECTOFFSETS | DIEFF_POLAR
    effect_desc.dwDuration = duration_us
    effect_desc.dwSamplePeriod = 0
    effect_desc.dwGain = DI_FFNOMINALMAX
    effect_desc.dwTriggerButton = DIEB_NOTRIGGER
    effect_desc.dwTriggerRepeatInterval = 0
    effect_desc.cAxes = axis_count
    effect_desc.rgdwAxes = C.cast(axes, POINTER(DWORD))
    effect_desc.rglDirection = C.cast(directions, POINTER(LONG))
    effect_desc.lpEnvelope = None
    effect_desc.cbTypeSpecificParams = C.sizeof(DICONSTANTFORCE)
    effect_desc.lpvTypeSpecificParams = C.cast(C.pointer(force), LPVOID)
    effect_desc.dwStartDelay = 0

    effect = device.CreateEffect(
        C.byref(GUID_ConstantForce),
        C.byref(effect_desc),
        None,
    )

    return ConstantForceEffectHandle(
        effect=effect,
        dieffect=effect_desc,
        axes=axes,
        directions=directions,
        force=force,
    )
