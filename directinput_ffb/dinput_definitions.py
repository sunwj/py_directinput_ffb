"""DirectInput constants, GUIDs, structures, and COM interfaces.

This module groups the pieces that mirror the DirectInput SDK headers:

- numeric constants (flags, object offsets, filter masks)
- COM interface IIDs and effect GUIDs
- ctypes structure layouts used by the COM methods
- comtypes interface declarations for IDirectInput8, device, and effect

The goal is to make the high-level logic in ``dinput_api.py`` readable without
burying it under pages of low-level declarations.
"""

from __future__ import annotations

from dataclasses import dataclass

from .dinput_types import (
    C,
    GUID,
    IUnknown,
    COMMETHOD,
    POINTER,
    HRESULT,
    DWORD,
    WORD,
    LONG,
    BOOL,
    HWND,
    HINSTANCE,
    HANDLE,
    LPVOID,
    LPCWSTR,
    WCHAR,
    MAX_PATH,
    REFGUID,
    LPGUID,
)

# ---------------------------------------------------------------------------
# Version and device enumeration constants
# ---------------------------------------------------------------------------

DIRECTINPUT_VERSION = 0x0800

DI8DEVCLASS_ALL = 0
DI8DEVCLASS_DEVICE = 1
DI8DEVCLASS_POINTER = 2
DI8DEVCLASS_KEYBOARD = 3
DI8DEVCLASS_GAMECTRL = 4

DIEDFL_ALLDEVICES = 0x00000000
DIEDFL_ATTACHEDONLY = 0x00000001
DIEDFL_FORCEFEEDBACK = 0x00000100

DIENUM_STOP = 0
DIENUM_CONTINUE = 1

# ---------------------------------------------------------------------------
# Cooperative level flags
# ---------------------------------------------------------------------------
#
# DirectInput requires one exclusivity flag and one focus flag.

DISCL_EXCLUSIVE = 0x00000001
DISCL_NONEXCLUSIVE = 0x00000002
DISCL_FOREGROUND = 0x00000004
DISCL_BACKGROUND = 0x00000008
DISCL_NOWINKEY = 0x00000010

# ---------------------------------------------------------------------------
# Effect flags and parameter masks
# ---------------------------------------------------------------------------

DIEFF_CARTESIAN = 0x00000010
DIEFF_POLAR = 0x00000020
DIEFF_SPHERICAL = 0x00000040
DIEFF_OBJECTIDS = 0x00000001
DIEFF_OBJECTOFFSETS = 0x00000002

DIEP_DURATION = 0x00000001
DIEP_SAMPLEPERIOD = 0x00000002
DIEP_GAIN = 0x00000004
DIEP_TRIGGERBUTTON = 0x00000008
DIEP_TRIGGERREPEATINTERVAL = 0x00000010
DIEP_AXES = 0x00000020
DIEP_DIRECTION = 0x00000040
DIEP_ENVELOPE = 0x00000080
DIEP_TYPESPECIFICPARAMS = 0x00000100
DIEP_START = 0x20000000
DIEP_ALLPARAMS = (
    DIEP_DURATION
    | DIEP_SAMPLEPERIOD
    | DIEP_GAIN
    | DIEP_TRIGGERBUTTON
    | DIEP_TRIGGERREPEATINTERVAL
    | DIEP_AXES
    | DIEP_DIRECTION
    | DIEP_ENVELOPE
    | DIEP_TYPESPECIFICPARAMS
)

DIEFT_ALL = 0x00000000

INFINITE = 0xFFFFFFFF
INFINITE_EFFECT_DURATION = INFINITE
DI_FFNOMINALMAX = 10000
DIEB_NOTRIGGER = 0xFFFFFFFF

# ---------------------------------------------------------------------------
# Joystick state offsets
# ---------------------------------------------------------------------------
#
# These match the layout commonly used by DirectInput joystick formats.

DIJOFS_X = 0
DIJOFS_Y = 4
DIJOFS_Z = 8
DIJOFS_RX = 12
DIJOFS_RY = 16
DIJOFS_RZ = 20
DIJOFS_SLIDER0 = 24
DIJOFS_SLIDER1 = 28

# ---------------------------------------------------------------------------
# DirectInput data-format object classification flags
# ---------------------------------------------------------------------------

DIDF_ABSAXIS = 0x00000001
DIDF_RELAXIS = 0x00000002

DIDFT_RELAXIS = 0x00000001
DIDFT_ABSAXIS = 0x00000002
DIDFT_AXIS = 0x00000003
DIDFT_PSHBUTTON = 0x00000004
DIDFT_TGLBUTTON = 0x00000008
DIDFT_BUTTON = 0x0000000C
DIDFT_POV = 0x00000010
DIDFT_COLLECTION = 0x00000040
DIDFT_NODATA = 0x00000080
DIDFT_ANYINSTANCE = 0x00FFFF00
DIDFT_OPTIONAL = 0x80000000

DIDOI_ASPECTPOSITION = 0x00000100

DIDFT_ALL = 0x00000000
DIDFT_AXIS = 0x00000003
DIDFT_FFACTUATOR = 0x01000000
DIDFT_OUTPUT = 0x10000000

# ---------------------------------------------------------------------------
# How to Get/Set device properties
# ---------------------------------------------------------------------------

DIPH_DEVICE = 0
DIPH_BYOFFSET = 1
DIPH_BYID = 2
DIPH_BYUSAGE = 3

# ---------------------------------------------------------------------------
# GUIDs
# ---------------------------------------------------------------------------

IID_IDirectInput8W = GUID("{BF798031-483A-4DA2-AA99-5D64ED369700}")
IID_IDirectInputDevice8W = GUID("{54D41081-DC15-4833-A41B-748F73A38179}")
IID_IDirectInputEffect = GUID("{E7E1F7C0-88D2-11D0-9AD0-00A0C9A06E35}")

GUID_ConstantForce = GUID("{13541C20-8E33-11D0-9AD0-00A0C9A06E35}")
GUID_RampForce = GUID("{13541C21-8E33-11D0-9AD0-00A0C9A06E35}")
GUID_Square = GUID("{13541C22-8E33-11D0-9AD0-00A0C9A06E35}")
GUID_Sine = GUID("{13541C23-8E33-11D0-9AD0-00A0C9A06E35}")
GUID_Triangle = GUID("{13541C24-8E33-11D0-9AD0-00A0C9A06E35}")
GUID_SawtoothUp = GUID("{13541C25-8E33-11D0-9AD0-00A0C9A06E35}")
GUID_SawtoothDown = GUID("{13541C26-8E33-11D0-9AD0-00A0C9A06E35}")
GUID_Spring = GUID("{13541C27-8E33-11D0-9AD0-00A0C9A06E35}")
GUID_Damper = GUID("{13541C28-8E33-11D0-9AD0-00A0C9A06E35}")
GUID_Inertia = GUID("{13541C29-8E33-11D0-9AD0-00A0C9A06E35}")
GUID_Friction = GUID("{13541C2A-8E33-11D0-9AD0-00A0C9A06E35}")
GUID_CustomForce = GUID("{13541C2B-8E33-11D0-9AD0-00A0C9A06E35}")

GUID_XAxis = GUID("{A36D02E0-C9F3-11CF-BFC7-444553540000}")
GUID_YAxis = GUID("{A36D02E1-C9F3-11CF-BFC7-444553540000}")
GUID_ZAxis = GUID("{A36D02E2-C9F3-11CF-BFC7-444553540000}")
GUID_RxAxis = GUID("{A36D02F4-C9F3-11CF-BFC7-444553540000}")
GUID_RyAxis = GUID("{A36D02F5-C9F3-11CF-BFC7-444553540000}")
GUID_RzAxis = GUID("{A36D02E3-C9F3-11CF-BFC7-444553540000}")
GUID_Slider = GUID("{A36D02E4-C9F3-11CF-BFC7-444553540000}")
GUID_POV = GUID("{A36D02F2-C9F3-11CF-BFC7-444553540000}")


def MAKEDIPROP(prop: int):
    return C.c_void_p(prop)

DIPROP_RANGE = MAKEDIPROP(4)
DIPROP_PHYSICALRANGE = MAKEDIPROP(18)
DIPROP_LOGICALRANGE = MAKEDIPROP(19)

# ---------------------------------------------------------------------------
# Helpful pure-Python model objects
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EnumeratedDeviceObjectInfo:
    """High-level Python view of one DirectInput device object."""

    guid_type: GUID
    name: str
    offset: int
    type_flags: int
    flags: int
    ff_max_force: int
    ff_force_resolution: int
    collection_number: int
    designator_index: int
    usage_page: int
    usage: int
    dimension: int
    exponent: int
    report_id: int

    @property
    def is_axis(self) -> bool:
        # The low byte stores the basic object type.  DIDFT_AXIS is 0x03.
        return bool(self.type_flags & DIDFT_AXIS)

    @property
    def is_ff_actuator(self) -> bool:
        return bool(self.type_flags & DIDFT_FFACTUATOR)

    @property
    def is_output(self) -> bool:
        return bool(self.type_flags & DIDFT_OUTPUT)
    

@dataclass(frozen=True)
class EnumeratedDevice:
    """Small Python-friendly representation of a DirectInput device.

    The raw callback receives a pointer to a ``DIDEVICEINSTANCEW`` structure.
    That structure is only guaranteed to be valid during the callback, so we
    immediately copy the fields we care about into this immutable dataclass.
    """

    guid_instance: GUID
    guid_product: GUID
    instance_name: str
    product_name: str
    usage_page: int
    usage: int
    device_type: int


@dataclass(frozen=True)
class EnumeratedEffect:
    """Python-friendly view of one effect type reported by EnumEffects."""

    guid: GUID
    name: str
    effect_type: int
    static_params: int
    dynamic_params: int


# ---------------------------------------------------------------------------
# ctypes structure declarations
# ---------------------------------------------------------------------------

class DIDEVICEOBJECTINSTANCEW(C.Structure):
    _fields_ = [
        ("dwSize", DWORD),
        ("guidType", GUID),
        ("dwOfs", DWORD),
        ("dwType", DWORD),
        ("dwFlags", DWORD),
        ("tszName", WCHAR * MAX_PATH),
        ("dwFFMaxForce", DWORD),
        ("dwFFForceResolution", DWORD),
        ("wCollectionNumber", WORD),
        ("wDesignatorIndex", WORD),
        ("wUsagePage", WORD),
        ("wUsage", WORD),
        ("dwDimension", DWORD),
        ("wExponent", WORD),
        ("wReportId", WORD),
    ]


class DIDEVICEINSTANCEW(C.Structure):
    _fields_ = [
        ("dwSize", DWORD),
        ("guidInstance", GUID),
        ("guidProduct", GUID),
        ("dwDevType", DWORD),
        ("tszInstanceName", WCHAR * MAX_PATH),
        ("tszProductName", WCHAR * MAX_PATH),
        ("guidFFDriver", GUID),
        ("wUsagePage", WORD),
        ("wUsage", WORD),
    ]


class DIEFFECTINFOW(C.Structure):
    _fields_ = [
        ("dwSize", DWORD),
        ("guid", GUID),
        ("dwEffType", DWORD),
        ("dwStaticParams", DWORD),
        ("dwDynamicParams", DWORD),
        ("tszName", WCHAR * MAX_PATH),
    ]


class DICONSTANTFORCE(C.Structure):
    _fields_ = [("lMagnitude", LONG)]


class DIRAMPFORCE(C.Structure):
    """Type-specific payload for a ramp effect.

    ``lStart`` and ``lEnd`` are signed magnitudes in the nominal DirectInput
    range of roughly ``-10000`` through ``10000``.
    """

    _fields_ = [
        ("lStart", LONG),
        ("lEnd", LONG),
    ]


class DIPERIODIC(C.Structure):
    """Type-specific payload for periodic effects.

    This structure is shared by square, sine, triangle, sawtooth-up, and
    sawtooth-down effects.
    """

    _fields_ = [
        ("dwMagnitude", DWORD),
        ("lOffset", LONG),
        ("dwPhase", DWORD),
        ("dwPeriod", DWORD),
    ]


class DICONDITION(C.Structure):
    """Type-specific payload for condition effects.

    Condition effects can use either one structure for the whole effect
    direction or one structure per axis.
    """

    _fields_ = [
        ("lOffset", LONG),
        ("lPositiveCoefficient", LONG),
        ("lNegativeCoefficient", LONG),
        ("dwPositiveSaturation", DWORD),
        ("dwNegativeSaturation", DWORD),
        ("lDeadBand", LONG),
    ]


class DIENVELOPE(C.Structure):
    _fields_ = [
        ("dwSize", DWORD),
        ("dwAttackLevel", DWORD),
        ("dwAttackTime", DWORD),
        ("dwFadeLevel", DWORD),
        ("dwFadeTime", DWORD),
    ]


class DIEFFECT(C.Structure):
    _fields_ = [
        ("dwSize", DWORD),
        ("dwFlags", DWORD),
        ("dwDuration", DWORD),
        ("dwSamplePeriod", DWORD),
        ("dwGain", DWORD),
        ("dwTriggerButton", DWORD),
        ("dwTriggerRepeatInterval", DWORD),
        ("cAxes", DWORD),
        ("rgdwAxes", POINTER(DWORD)),
        ("rglDirection", POINTER(LONG)),
        ("lpEnvelope", POINTER(DIENVELOPE)),
        ("cbTypeSpecificParams", DWORD),
        ("lpvTypeSpecificParams", LPVOID),
        ("dwStartDelay", DWORD),
    ]


class DIOBJECTDATAFORMAT(C.Structure):
    _fields_ = [
        ("pguid", POINTER(GUID)),
        ("dwOfs", DWORD),
        ("dwType", DWORD),
        ("dwFlags", DWORD),
    ]


class DIDATAFORMAT(C.Structure):
    _fields_ = [
        ("dwSize", DWORD),
        ("dwObjSize", DWORD),
        ("dwFlags", DWORD),
        ("dwDataSize", DWORD),
        ("dwNumObjs", DWORD),
        ("rgodf", POINTER(DIOBJECTDATAFORMAT)),
    ]


class DIJOYSTATE(C.Structure):
    """state buffer for a two-axis joystick format.

    ``SetDataFormat`` does not describe the device's internal memory layout.
    It describes the layout *our application* expects when polling the device.
    The ``dwOfs`` values in ``DIOBJECTDATAFORMAT`` therefore point into this
    structure's fields.
    """
    _fields_ = [
        ("lX", LONG),
        ("lY", LONG),
        ("lZ", LONG),
        ("lRx", LONG),
        ("lRy", LONG),
        ("lRz", LONG),
        ("rglSlider", LONG * 2),
        ("rgdwPOV", DWORD * 4),
        ("rgbButtons", C.c_ubyte * 32),
    ]

    def __str__(self):
        return f'lX: {self.lX}, lY: {self.lY}'


# ---------------------------------------------------------------------------
# For device properties
# ---------------------------------------------------------------------------

class DIPROPHEADER(C.Structure):
    _fields_ = [
        ("dwSize", DWORD),
        ("dwHeaderSize", DWORD),
        ("dwObj", DWORD),
        ("dwHow", DWORD),
    ]

class DIPROPRANGE(C.Structure):
    _fields_ = [
        ("diph", DIPROPHEADER),
        ("lMin", LONG),
        ("lMax", LONG),
    ]

# ---------------------------------------------------------------------------
# Callback prototypes
# ---------------------------------------------------------------------------

LPDIDEVICEOBJECTINSTANCEW = POINTER(DIDEVICEOBJECTINSTANCEW)
LPDIDEVICEINSTANCEW = POINTER(DIDEVICEINSTANCEW)
LPDIEFFECTINFOW = POINTER(DIEFFECTINFOW)

LPDIENUMDEVICEOBJECTSCALLBACKW = C.WINFUNCTYPE(BOOL, LPDIDEVICEOBJECTINSTANCEW, LPVOID)
LPDIENUMDEVICESCALLBACKW = C.WINFUNCTYPE(BOOL, LPDIDEVICEINSTANCEW, LPVOID)
LPDIENUMEFFECTSCALLBACKW = C.WINFUNCTYPE(BOOL, LPDIEFFECTINFOW, LPVOID)


# ---------------------------------------------------------------------------
# COM interface declarations
# ---------------------------------------------------------------------------
#
# DirectInput is a COM API. Method *order* matters: if the declarations do not
# match the native vtable order, later calls will jump into the wrong function.

class IDirectInputEffect(IUnknown):
    _iid_ = IID_IDirectInputEffect
    _methods_ = [
        COMMETHOD([], HRESULT, "Initialize",
                  (["in"], HINSTANCE, "hinst"),
                  (["in"], DWORD, "dwVersion"),
                  (["in"], REFGUID, "rguid")),
        COMMETHOD([], HRESULT, "GetEffectGuid",
                  (["out"], LPGUID, "pguid")),
        COMMETHOD([], HRESULT, "GetParameters",
                  (["in", "out"], POINTER(DIEFFECT), "peff"),
                  (["in"], DWORD, "dwFlags")),
        COMMETHOD([], HRESULT, "SetParameters",
                  (["in"], POINTER(DIEFFECT), "peff"),
                  (["in"], DWORD, "dwFlags")),
        COMMETHOD([], HRESULT, "Start",
                  (["in"], DWORD, "dwIterations"),
                  (["in"], DWORD, "dwFlags")),
        COMMETHOD([], HRESULT, "Stop"),
        COMMETHOD([], HRESULT, "GetEffectStatus",
                  (["out"], POINTER(DWORD), "pdwFlags")),
        COMMETHOD([], HRESULT, "Download"),
        COMMETHOD([], HRESULT, "Unload"),
        COMMETHOD([], HRESULT, "Escape",
                  (["in", "out"], LPVOID, "pesc")),
    ]


class IDirectInputDevice8W(IUnknown):
    _iid_ = IID_IDirectInputDevice8W
    _methods_ = [
        COMMETHOD([], HRESULT, "GetCapabilities",
                  (["in", "out"], LPVOID, "lpDIDevCaps")),
        COMMETHOD([], HRESULT, "EnumObjects",
                  (["in"], LPDIENUMDEVICEOBJECTSCALLBACKW, "lpCallback"),
                  (["in"], LPVOID, "pvRef"),
                  (["in"], DWORD, "dwFlags")),
        COMMETHOD([], HRESULT, "GetProperty",
                  (["in"], LPVOID, "rguidProp"),
                  (["in"], LPVOID, "pdiph")),
        COMMETHOD([], HRESULT, "SetProperty",
                  (["in"], LPVOID, "rguidProp"),
                  (["in"], LPVOID, "pdiph")),
        COMMETHOD([], HRESULT, "Acquire"),
        COMMETHOD([], HRESULT, "Unacquire"),
        COMMETHOD([], HRESULT, "GetDeviceState",
                  (["in"], DWORD, "cbData"),
                  (["in"], LPVOID, "lpvData")),
        COMMETHOD([], HRESULT, "GetDeviceData",
                  (["in"], DWORD, "cbObjectData"),
                  (["out"], LPVOID, "rgdod"),
                  (["in", "out"], POINTER(DWORD), "pdwInOut"),
                  (["in"], DWORD, "dwFlags")),
        COMMETHOD([], HRESULT, "SetDataFormat",
                  (["in"], POINTER(DIDATAFORMAT), "lpdf")),
        COMMETHOD([], HRESULT, "SetEventNotification",
                  (["in"], HANDLE, "hEvent")),
        COMMETHOD([], HRESULT, "SetCooperativeLevel",
                  (["in"], HWND, "hwnd"),
                  (["in"], DWORD, "dwFlags")),
        COMMETHOD([], HRESULT, "GetObjectInfo",
                  (["in", "out"], LPVOID, "pdidoi"),
                  (["in"], DWORD, "dwObj"),
                  (["in"], DWORD, "dwHow")),
        COMMETHOD([], HRESULT, "GetDeviceInfo",
                  (["in", "out"], LPVOID, "pdidi")),
        COMMETHOD([], HRESULT, "RunControlPanel",
                  (["in"], HWND, "hwndOwner"),
                  (["in"], DWORD, "dwFlags")),
        COMMETHOD([], HRESULT, "Initialize",
                  (["in"], HINSTANCE, "hinst"),
                  (["in"], DWORD, "dwVersion"),
                  (["in"], REFGUID, "rguid")),
        COMMETHOD([], HRESULT, "CreateEffect",
                  (["in"], REFGUID, "rguid"),
                  (["in"], POINTER(DIEFFECT), "lpeff"),
                  (["out"], POINTER(POINTER(IDirectInputEffect)), "ppdeff"),
                  (["in"], LPVOID, "punkOuter")),
        COMMETHOD([], HRESULT, "EnumEffects",
                  (["in"], LPDIENUMEFFECTSCALLBACKW, "lpCallback"),
                  (["in"], LPVOID, "pvRef"),
                  (["in"], DWORD, "dwEffType")),
        COMMETHOD([], HRESULT, "GetEffectInfo",
                  (["in", "out"], LPVOID, "pdei"),
                  (["in"], REFGUID, "rguid")),
        COMMETHOD([], HRESULT, "GetForceFeedbackState",
                  (["out"], POINTER(DWORD), "pdwOut")),
        COMMETHOD([], HRESULT, "SendForceFeedbackCommand",
                  (["in"], DWORD, "dwFlags")),
        COMMETHOD([], HRESULT, "EnumCreatedEffectObjects",
                  (["in"], LPVOID, "lpCallback"),
                  (["in"], LPVOID, "pvRef"),
                  (["in"], DWORD, "fl")),
        COMMETHOD([], HRESULT, "Escape",
                  (["in", "out"], LPVOID, "pesc")),
        COMMETHOD([], HRESULT, "Poll"),
        COMMETHOD([], HRESULT, "SendDeviceData",
                  (["in"], DWORD, "cbObjectData"),
                  (["in"], LPVOID, "rgdod"),
                  (["in", "out"], POINTER(DWORD), "pdwInOut"),
                  (["in"], DWORD, "fl")),
        COMMETHOD([], HRESULT, "EnumEffectsInFile",
                  (["in"], LPCWSTR, "lpszFileName"),
                  (["in"], LPVOID, "lpCallback"),
                  (["in"], LPVOID, "pvRef"),
                  (["in"], DWORD, "dwFlags")),
        COMMETHOD([], HRESULT, "WriteEffectToFile",
                  (["in"], LPCWSTR, "lpszFileName"),
                  (["in"], DWORD, "dwEntries"),
                  (["in"], LPVOID, "rgDiFileEft"),
                  (["in"], DWORD, "dwFlags")),
        COMMETHOD([], HRESULT, "BuildActionMap",
                  (["in", "out"], LPVOID, "lpdiaf"),
                  (["in"], LPCWSTR, "lpszUserName"),
                  (["in"], DWORD, "dwFlags")),
        COMMETHOD([], HRESULT, "SetActionMap",
                  (["in"], LPVOID, "lpdiaf"),
                  (["in"], LPCWSTR, "lpszUserName"),
                  (["in"], DWORD, "dwFlags")),
        COMMETHOD([], HRESULT, "GetImageInfo",
                  (["in", "out"], LPVOID, "lpdiDevImageInfoHeader")),
    ]


class IDirectInput8W(IUnknown):
    _iid_ = IID_IDirectInput8W
    _methods_ = [
        COMMETHOD([], HRESULT, "CreateDevice",
                  (["in"], REFGUID, "rguid"),
                  (["out"], POINTER(POINTER(IDirectInputDevice8W)), "lplpDirectInputDevice"),
                  (["in"], LPVOID, "pUnkOuter")),
        COMMETHOD([], HRESULT, "EnumDevices",
                  (["in"], DWORD, "dwDevType"),
                  (["in"], LPDIENUMDEVICESCALLBACKW, "lpCallback"),
                  (["in"], LPVOID, "pvRef"),
                  (["in"], DWORD, "dwFlags")),
        COMMETHOD([], HRESULT, "GetDeviceStatus",
                  (["in"], REFGUID, "rguidInstance")),
        COMMETHOD([], HRESULT, "RunControlPanel",
                  (["in"], HWND, "hwndOwner"),
                  (["in"], DWORD, "dwFlags")),
        COMMETHOD([], HRESULT, "Initialize",
                  (["in"], HINSTANCE, "hinst"),
                  (["in"], DWORD, "dwVersion")),
        COMMETHOD([], HRESULT, "FindDevice",
                  (["in"], REFGUID, "rguidClass"),
                  (["in"], LPCWSTR, "ptszName"),
                  (["out"], LPGUID, "pguidInstance")),
        COMMETHOD([], HRESULT, "EnumDevicesBySemantics",
                  (["in"], LPCWSTR, "ptszUserName"),
                  (["in"], LPVOID, "lpdiActionFormat"),
                  (["in"], LPVOID, "lpCallback"),
                  (["in"], LPVOID, "pvRef"),
                  (["in"], DWORD, "dwFlags")),
        COMMETHOD([], HRESULT, "ConfigureDevices",
                  (["in"], LPVOID, "lpdiConfigureDevicesCallback"),
                  (["in"], LPVOID, "lpdiCDParams"),
                  (["in"], DWORD, "dwFlags"),
                  (["in"], LPVOID, "pvRefData")),
    ]


__all__ = [name for name in globals() if name.isupper() or name.startswith("IDirect") or name.startswith("DI") or name.startswith("GUID_") or name in {
    "EnumeratedDeviceObjectInfo",
    "EnumeratedDevice",
    "EnumeratedEffect",
    "DIDEVICEOBJECTINSTANCEW",
    "DIDEVICEINSTANCEW",
    "DIEFFECTINFOW",
    "DICONSTANTFORCE",
    "DIRAMPFORCE",
    "DIPERIODIC",
    "DICONDITION",
    "DIENVELOPE",
    "DIEFFECT",
    "DIOBJECTDATAFORMAT",
    "DIDATAFORMAT",
    "DIJOYSTATE",
    "LPDIENUMDEVICESCALLBACKW",
    "LPDIENUMEFFECTSCALLBACKW",
    "LPDIDEVICEOBJECTINSTANCEW",
    "LPDIENUMDEVICEOBJECTSCALLBACKW",
    "DIPROPHEADER",
    "DIPROPRANGE"
}]
