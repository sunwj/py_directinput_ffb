"""High-level DirectInput helper functions.

This module contains the logic that a reader usually cares about first:

- create the DirectInput root object
- enumerate force-feedback game controllers
- open one device
- set cooperative level and data format
- acquire/unacquire the device
- enumerate supported effects

The low-level types and COM declarations are imported from sibling modules so
that these functions stay readable.
"""

from __future__ import annotations

from typing import List

from dinput_types import C, GUID, LPVOID, POINTER, HWND, kernel32, user32, DirectInput8Create
from dinput_definitions import (
    DIRECTINPUT_VERSION,
    IID_IDirectInput8W,
    IDirectInput8W,
    IDirectInputDevice8W,
    DI8DEVCLASS_GAMECTRL,
    DIEDFL_ALLDEVICES,
    DIEDFL_ATTACHEDONLY,
    DIEDFL_FORCEFEEDBACK,
    DIENUM_CONTINUE,
    DISCL_EXCLUSIVE,
    DISCL_NONEXCLUSIVE,
    DISCL_BACKGROUND,
    DISCL_FOREGROUND,
    GUID_XAxis,
    GUID_YAxis,
    DIDFT_AXIS,
    DIDFT_ANYINSTANCE,
    DIDFT_OPTIONAL,
    DIDOI_ASPECTPOSITION,
    DIOBJECTDATAFORMAT,
    DIDATAFORMAT,
    MiniJoystickState,
    LPDIENUMDEVICESCALLBACKW,
    LPDIENUMEFFECTSCALLBACKW,
    EnumeratedDevice,
    EnumeratedEffect,
)


def check_hr(hr: int, what: str = "DirectInput call") -> int:
    """Raise ``OSError`` when an HRESULT indicates failure.

    ``comtypes`` often raises ``COMError`` directly when a COM method fails,
    but some calls still return HRESULT values explicitly. This helper gives us
    one consistent place to translate a negative HRESULT into a readable Python
    exception.
    """

    hr = int(hr)
    if hr < 0:
        raise OSError(f"{what} failed: HRESULT=0x{hr & 0xFFFFFFFF:08X}")
    return hr


# ---------------------------------------------------------------------------
# Hidden helper window for cooperative level
# ---------------------------------------------------------------------------
#
# DirectInput expects a real top-level window handle from our process. The
# original working script correctly switched away from the console window and
# instead created a small hidden window. We preserve that behaviour here.

_hwnd_keepalive: HWND | None = None


def get_ffb_hwnd() -> HWND:
    """Create or return a persistent hidden helper window.

    The window uses the built-in ``STATIC`` class, mirroring the approach from
    the C++ sample that inspired the final working Python script. The returned
    ``HWND`` is cached globally because cooperative level and acquisition depend
    on the handle remaining valid for the lifetime of the device.
    """

    global _hwnd_keepalive

    if _hwnd_keepalive and user32.IsWindow(_hwnd_keepalive):
        return _hwnd_keepalive

    hinst = kernel32.GetModuleHandleW(None)
    hwnd = user32.CreateWindowExW(
        0,
        "STATIC",
        "FFB_EXAMPLE",
        0,
        0,
        0,
        10,
        10,
        None,
        None,
        hinst,
        None,
    )
    if not hwnd:
        raise C.WinError(C.get_last_error())

    _hwnd_keepalive = hwnd
    return hwnd


# ---------------------------------------------------------------------------
# Root DirectInput creation and device enumeration
# ---------------------------------------------------------------------------

_device_enum_callbacks = []
_effect_enum_callbacks = []


def create_direct_input() -> POINTER(IDirectInput8W):
    """Create the top-level ``IDirectInput8W`` COM object."""

    out_ptr = LPVOID()
    hinst = kernel32.GetModuleHandleW(None)

    hr = DirectInput8Create(
        hinst,
        DIRECTINPUT_VERSION,
        C.byref(IID_IDirectInput8W),
        C.byref(out_ptr),
        None,
    )
    check_hr(hr, "DirectInput8Create")
    return C.cast(out_ptr, POINTER(IDirectInput8W))


def enum_devices(
    di: POINTER(IDirectInput8W),
    *,
    only_attached: bool = True,
    only_force_feedback: bool = False,
) -> List[EnumeratedDevice]:
    """Enumerate game-controller devices visible to DirectInput.

    The callback receives transient C structures. We therefore copy each device
    into a small Python dataclass immediately.
    """

    devices: List[EnumeratedDevice] = []

    flags = DIEDFL_ATTACHEDONLY if only_attached else DIEDFL_ALLDEVICES
    if only_force_feedback:
        flags |= DIEDFL_FORCEFEEDBACK

    def _cb(lpddi, _pvref):
        inst = lpddi.contents
        devices.append(
            EnumeratedDevice(
                guid_instance=GUID(str(inst.guidInstance)),
                guid_product=GUID(str(inst.guidProduct)),
                instance_name=inst.tszInstanceName,
                product_name=inst.tszProductName,
                usage_page=inst.wUsagePage,
                usage=inst.wUsage,
                device_type=inst.dwDevType,
            )
        )
        return DIENUM_CONTINUE

    cb = LPDIENUMDEVICESCALLBACKW(_cb)
    _device_enum_callbacks.append(cb)

    hr = di.EnumDevices(DI8DEVCLASS_GAMECTRL, cb, None, flags)
    check_hr(hr, "IDirectInput8W.EnumDevices")
    return devices


def create_device(
    di: POINTER(IDirectInput8W),
    guid_instance: GUID,
) -> POINTER(IDirectInputDevice8W):
    """Open one DirectInput device given its instance GUID."""

    return di.CreateDevice(C.byref(guid_instance), None)


# ---------------------------------------------------------------------------
# Cooperative level and data format setup
# ---------------------------------------------------------------------------


def set_cooperative_level(
    device: POINTER(IDirectInputDevice8W),
    *,
    hwnd: HWND | None = None,
    exclusive: bool = True,
    background: bool = True,
) -> HWND:
    """Configure how the application shares the device with the rest of Windows.

    Parameters
    ----------
    exclusive:
        When ``True``, DirectInput requests exclusive access. This is commonly
        required for force-feedback playback.
    background:
        When ``True``, the device remains usable when the process window is not
        in the foreground.

    Returns
    -------
    HWND
        The window handle actually used. Returning it makes the calling code
        explicit about which window must stay alive.
    """

    hwnd = hwnd or get_ffb_hwnd()

    flags = 0
    flags |= DISCL_EXCLUSIVE if exclusive else DISCL_NONEXCLUSIVE
    flags |= DISCL_BACKGROUND if background else DISCL_FOREGROUND

    hr = device.SetCooperativeLevel(hwnd, flags)
    check_hr(hr, "IDirectInputDevice8W.SetCooperativeLevel")
    return hwnd


def build_minimal_xy_data_format() -> DIDATAFORMAT:
    """Build a minimal application data format for X/Y joystick axes.

    This format is intentionally small because the original working script only
    needed enough state information to satisfy DirectInput and create force
    effects on a two-axis device layout.

    Important:
    ``dwOfs`` points into *our* state buffer, represented by ``MiniJoystickState``.
    Those offsets are not arbitrary device offsets; they define how polled input
    would be packed if we later called ``GetDeviceState``.
    """

    objs = (DIOBJECTDATAFORMAT * 2)()

    objs[0].pguid = C.pointer(GUID_XAxis)
    objs[0].dwOfs = 0
    objs[0].dwType = DIDFT_AXIS | DIDFT_ANYINSTANCE | DIDFT_OPTIONAL
    objs[0].dwFlags = DIDOI_ASPECTPOSITION

    objs[1].pguid = C.pointer(GUID_YAxis)
    objs[1].dwOfs = 4
    objs[1].dwType = DIDFT_AXIS | DIDFT_ANYINSTANCE | DIDFT_OPTIONAL
    objs[1].dwFlags = DIDOI_ASPECTPOSITION

    data_format = DIDATAFORMAT()
    data_format.dwSize = C.sizeof(DIDATAFORMAT)
    data_format.dwObjSize = C.sizeof(DIOBJECTDATAFORMAT)
    data_format.dwFlags = 0
    data_format.dwDataSize = C.sizeof(MiniJoystickState)
    data_format.dwNumObjs = 2
    data_format.rgodf = objs

    # Keep the backing arrays and GUID objects alive as long as the returned
    # DIDATAFORMAT instance is alive. Without this, Python could free memory
    # still referenced by DirectInput.
    data_format._objs_ref = objs
    data_format._guid_refs = [GUID_XAxis, GUID_YAxis]
    return data_format


def set_data_format(
    device: POINTER(IDirectInputDevice8W),
    data_format: DIDATAFORMAT | None = None,
) -> DIDATAFORMAT:
    """Apply a data format to a DirectInput device.

    Returning the format object is useful because callers often need to hold on
    to it so its backing arrays stay alive.
    """

    if data_format is None:
        data_format = build_minimal_xy_data_format()

    hr = device.SetDataFormat(C.byref(data_format))
    check_hr(hr, "IDirectInputDevice8W.SetDataFormat")
    return data_format


def acquire(device: POINTER(IDirectInputDevice8W)) -> None:
    """Acquire a DirectInput device for use."""

    hr = device.Acquire()
    check_hr(hr, "IDirectInputDevice8W.Acquire")


def unacquire(device: POINTER(IDirectInputDevice8W)) -> None:
    """Release a previously acquired device."""

    hr = device.Unacquire()
    check_hr(hr, "IDirectInputDevice8W.Unacquire")


# ---------------------------------------------------------------------------
# Effect capability enumeration
# ---------------------------------------------------------------------------


def enum_effects(device: POINTER(IDirectInputDevice8W)) -> List[EnumeratedEffect]:
    """Enumerate effect types supported by a device."""

    effects: List[EnumeratedEffect] = []

    def _cb(lpdei, _pvref):
        info = lpdei.contents
        effects.append(
            EnumeratedEffect(
                guid=GUID(str(info.guid)),
                name=info.tszName,
                effect_type=info.dwEffType,
                static_params=info.dwStaticParams,
                dynamic_params=info.dwDynamicParams,
            )
        )
        return DIENUM_CONTINUE

    cb = LPDIENUMEFFECTSCALLBACKW(_cb)
    _effect_enum_callbacks.append(cb)

    hr = device.EnumEffects(cb, None, 0)
    check_hr(hr, "IDirectInputDevice8W.EnumEffects")
    return effects
