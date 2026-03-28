import ctypes as C
from ctypes import wintypes as W
import comtypes
from comtypes import GUID, IUnknown, COMMETHOD, POINTER, STDMETHOD, HRESULT


# ============================================================
# Basic Win32 / DirectInput types
# ============================================================

DWORD = W.DWORD
WORD = W.WORD
LONG = W.LONG
ULONG = W.ULONG
UINT = W.UINT
BOOL = W.BOOL
HWND = W.HWND
HINSTANCE = W.HINSTANCE
HMENU = W.HMENU
LPVOID = C.c_void_p
LPCVOID = C.c_void_p
LPCWSTR = W.LPCWSTR
WCHAR = W.WCHAR
CHAR = C.c_char
MAX_PATH = 260

REFGUID = POINTER(GUID)
LPGUID = POINTER(GUID)


# ============================================================
# DLL bindings
# ============================================================

dinput8 = C.WinDLL("dinput8.dll")
kernel32 = C.WinDLL("kernel32.dll")
user32 = C.WinDLL("user32.dll")

user32.CreateWindowExW.argtypes = [
    DWORD, LPCWSTR, LPCWSTR, DWORD,
    C.c_int, C.c_int, C.c_int, C.c_int,
    HWND, HMENU, HINSTANCE, LPVOID
]
user32.CreateWindowExW.restype = HWND

user32.IsWindow.argtypes = [HWND]
user32.IsWindow.restype = BOOL

kernel32.GetModuleHandleW.argtypes = [W.LPCWSTR]
kernel32.GetModuleHandleW.restype = HINSTANCE

DirectInput8Create = dinput8.DirectInput8Create
DirectInput8Create.argtypes = [
    HINSTANCE,
    DWORD,
    C.POINTER(GUID),
    C.POINTER(LPVOID),
    LPVOID,
]
DirectInput8Create.restype = HRESULT

_hwnd_keepalive = None
def get_ffb_hwnd():
    global _hwnd_keepalive
    if _hwnd_keepalive and user32.IsWindow(_hwnd_keepalive):
        return _hwnd_keepalive

    hinst = kernel32.GetModuleHandleW(None)

    # Built-in STATIC class, same idea as the C++ example.
    hwnd = user32.CreateWindowExW(
        0,
        "STATIC",
        "FFB_EXAMPLE",
        0,          # style
        0, 0, 10, 10,
        None, None,
        hinst,
        None,
    )
    if not hwnd:
        raise C.WinError(C.get_last_error())

    _hwnd_keepalive = hwnd
    return hwnd


# ============================================================
# HRESULT helpers
# ============================================================

def check_hr(hr, what="DirectInput call"):
    hr = int(hr)
    if hr < 0:
        raise OSError(f"{what} failed: HRESULT=0x{hr & 0xffffffff:08X}")
    return hr


# ============================================================
# DirectInput constants
# ============================================================

DIRECTINPUT_VERSION = 0x0800

# Device classes
DI8DEVCLASS_ALL = 0
DI8DEVCLASS_DEVICE = 1
DI8DEVCLASS_POINTER = 2
DI8DEVCLASS_KEYBOARD = 3
DI8DEVCLASS_GAMECTRL = 4

# Enumeration flags
DIEDFL_ALLDEVICES = 0x00000000
DIEDFL_ATTACHEDONLY = 0x00000001
DIEDFL_FORCEFEEDBACK = 0x00000100

# Enum callback return values
DIENUM_STOP = 0
DIENUM_CONTINUE = 1

# Cooperative level flags
DISCL_EXCLUSIVE = 0x00000001
DISCL_NONEXCLUSIVE = 0x00000002
DISCL_FOREGROUND = 0x00000004
DISCL_BACKGROUND = 0x00000008
DISCL_NOWINKEY = 0x00000010

# Effect flags
DIEFF_CARTESIAN = 0x00000001
DIEFF_POLAR = 0x00000002
DIEFF_SPHERICAL = 0x00000004
DIEFF_OBJECTIDS = 0x00000008
DIEFF_OBJECTOFFSETS = 0x00000010

# Effect parameter flags
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

# Effect type filters
DIEFT_ALL = 0x00000000

# Misc
INFINITE = 0xFFFFFFFF
DI_FFNOMINALMAX = 10000
DIPROP_BUFFERSIZE = 1

# Common object offsets from dinput.h
DIJOFS_X = 0
DIJOFS_Y = 4
DIJOFS_Z = 8
DIJOFS_RX = 12
DIJOFS_RY = 16
DIJOFS_RZ = 20
DIJOFS_SLIDER0 = 24
DIJOFS_SLIDER1 = 28

# Infinite effect duration in microseconds
INFINITE_EFFECT_DURATION = INFINITE

# Trigger button "none"
DIEB_NOTRIGGER = 0xFFFFFFFF


# ============================================================
# GUIDs
# ============================================================

IID_IDirectInput8W = GUID("{BF798031-483A-4DA2-AA99-5D64ED369700}")
IID_IDirectInputDevice8W = GUID("{54D41081-DC15-4833-A41B-748F73A38179}")
IID_IDirectInputEffect = GUID("{E7E1F7C0-88D2-11D0-9AD0-00A0C9A06E35}")

GUID_ConstantForce = GUID("{13541C20-8E33-11D0-9AD0-00A0C9A06E35}")


# ============================================================
# Structures
# ============================================================

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
    _fields_ = [
        ("lMagnitude", LONG),
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


# These are needed for SetDataFormat.
class DIOBJECTDATAFORMAT(C.Structure):
    _fields_ = [
        ("pguid", LPGUID),
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


# ============================================================
# Callback prototypes
# ============================================================

LPDIDEVICEINSTANCEW = POINTER(DIDEVICEINSTANCEW)
LPDIEFFECTINFOW = POINTER(DIEFFECTINFOW)

LPDIENUMDEVICESCALLBACKW = C.WINFUNCTYPE(BOOL, LPDIDEVICEINSTANCEW, LPVOID)
LPDIENUMEFFECTSCALLBACKW = C.WINFUNCTYPE(BOOL, LPDIEFFECTINFOW, LPVOID)


# ============================================================
# COM interface declarations
# ============================================================

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
        # IUnknown + IDirectInputDevice methods in exact order matter.
        COMMETHOD([], HRESULT, "GetCapabilities",
                  (["in", "out"], LPVOID, "lpDIDevCaps")),
        COMMETHOD([], HRESULT, "EnumObjects",
                  (["in"], LPVOID, "lpCallback"),
                  (["in"], LPVOID, "pvRef"),
                  (["in"], DWORD, "dwFlags")),
        COMMETHOD([], HRESULT, "GetProperty",
                  (["in"], REFGUID, "rguidProp"),
                  (["in", "out"], LPVOID, "pdiph")),
        COMMETHOD([], HRESULT, "SetProperty",
                  (["in"], REFGUID, "rguidProp"),
                  (["in"], LPVOID, "pdiph")),
        COMMETHOD([], HRESULT, "Acquire"),
        COMMETHOD([], HRESULT, "Unacquire"),
        COMMETHOD([], HRESULT, "GetDeviceState",
                  (["in"], DWORD, "cbData"),
                  (["out"], LPVOID, "lpvData")),
        COMMETHOD([], HRESULT, "GetDeviceData",
                  (["in"], DWORD, "cbObjectData"),
                  (["out"], LPVOID, "rgdod"),
                  (["in", "out"], POINTER(DWORD), "pdwInOut"),
                  (["in"], DWORD, "dwFlags")),
        COMMETHOD([], HRESULT, "SetDataFormat",
                  (["in"], POINTER(DIDATAFORMAT), "lpdf")),
        COMMETHOD([], HRESULT, "SetEventNotification",
                  (["in"], W.HANDLE, "hEvent")),
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
                  (["in"], W.LPCWSTR, "lpszFileName"),
                  (["in"], LPVOID, "lpCallback"),
                  (["in"], LPVOID, "pvRef"),
                  (["in"], DWORD, "dwFlags")),
        COMMETHOD([], HRESULT, "WriteEffectToFile",
                  (["in"], W.LPCWSTR, "lpszFileName"),
                  (["in"], DWORD, "dwEntries"),
                  (["in"], LPVOID, "rgDiFileEft"),
                  (["in"], DWORD, "dwFlags")),
        COMMETHOD([], HRESULT, "BuildActionMap",
                  (["in", "out"], LPVOID, "lpdiaf"),
                  (["in"], W.LPCWSTR, "lpszUserName"),
                  (["in"], DWORD, "dwFlags")),
        COMMETHOD([], HRESULT, "SetActionMap",
                  (["in"], LPVOID, "lpdiaf"),
                  (["in"], W.LPCWSTR, "lpszUserName"),
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
                  (["in"], W.LPCWSTR, "ptszName"),
                  (["out"], LPGUID, "pguidInstance")),
        COMMETHOD([], HRESULT, "EnumDevicesBySemantics",
                  (["in"], W.LPCWSTR, "ptszUserName"),
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


# ============================================================
# Root creation
# ============================================================

def create_direct_input():
    """
    Create and return IDirectInput8W.
    """
    p = LPVOID()
    hinst = kernel32.GetModuleHandleW(None)

    hr = DirectInput8Create(
        hinst,
        DIRECTINPUT_VERSION,
        C.byref(IID_IDirectInput8W),
        C.byref(p),
        None,
    )
    check_hr(hr, "DirectInput8Create")

    return C.cast(p, POINTER(IDirectInput8W))


# ============================================================
# Device enumeration
# ============================================================

_device_enum_callbacks = []


def enum_devices(di, only_attached=True, only_force_feedback=False):
    """
    Enumerate devices and return a list of dictionaries.
    """
    results = []

    flags = DIEDFL_ATTACHEDONLY if only_attached else DIEDFL_ALLDEVICES
    if only_force_feedback:
        flags |= DIEDFL_FORCEFEEDBACK

    def _cb(lpddi, pvref):
        inst = lpddi.contents
        results.append({
            "guidInstance": GUID(str(inst.guidInstance)),
            "guidProduct": GUID(str(inst.guidProduct)),
            "instance_name": inst.tszInstanceName,
            "product_name": inst.tszProductName,
            "usage_page": inst.wUsagePage,
            "usage": inst.wUsage,
            "dwDevType": inst.dwDevType,
        })
        return DIENUM_CONTINUE

    cb = LPDIENUMDEVICESCALLBACKW(_cb)
    _device_enum_callbacks.append(cb)

    hr = di.EnumDevices(
        DI8DEVCLASS_GAMECTRL,
        cb,
        None,
        flags,
    )
    check_hr(hr, "IDirectInput8W.EnumDevices")
    return results


# ============================================================
# Create device
# ============================================================

def create_device(di, guid_instance):
    """
    guid_instance can be a comtypes.GUID instance.
    Returns POINTER(IDirectInputDevice8W).
    """
    device = di.CreateDevice(C.byref(guid_instance), None)
    return device


# ============================================================
# Window helper
# ============================================================

def get_console_hwnd():
    kernel32.GetConsoleWindow.restype = HWND
    hwnd = kernel32.GetConsoleWindow()
    if not hwnd:
        raise RuntimeError("No console HWND available; use a real GUI window handle.")
    return hwnd


# ============================================================
# Cooperative level
# ============================================================

def set_cooperative_level(device, hwnd=None,
                          exclusive=True,
                          background=True):
    if hwnd is None:
        # hwnd = get_console_hwnd()
        hwnd = get_ffb_hwnd()

    flags = 0
    flags |= DISCL_EXCLUSIVE if exclusive else DISCL_NONEXCLUSIVE
    flags |= DISCL_BACKGROUND if background else DISCL_FOREGROUND

    hr = device.SetCooperativeLevel(hwnd, flags)
    check_hr(hr, "IDirectInputDevice8W.SetCooperativeLevel")


# ============================================================
# Data format
# ============================================================

# DirectInput object-type bits
DIDFT_ABSAXIS      = 0x00000001
DIDFT_RELAXIS      = 0x00000002
DIDFT_AXIS         = 0x00000003
DIDFT_PSHBUTTON    = 0x00000004
DIDFT_TGLBUTTON    = 0x00000008
DIDFT_BUTTON       = 0x0000000C
DIDFT_POV          = 0x00000010
DIDFT_COLLECTION   = 0x00000040
DIDFT_NODATA       = 0x00000080

DIDFT_ANYINSTANCE  = 0x00FFFF00
DIDFT_OPTIONAL     = 0x80000000

# Object aspect flags
DIDOI_ASPECTPOSITION = 0x00000100

# Standard object GUIDs
GUID_XAxis = GUID("{A36D02E0-C9F3-11CF-BFC7-444553540000}")
GUID_YAxis = GUID("{A36D02E1-C9F3-11CF-BFC7-444553540000}")
GUID_ZAxis = GUID("{A36D02E2-C9F3-11CF-BFC7-444553540000}")
GUID_RxAxis = GUID("{A36D02F4-C9F3-11CF-BFC7-444553540000}")
GUID_RyAxis = GUID("{A36D02F5-C9F3-11CF-BFC7-444553540000}")
GUID_RzAxis = GUID("{A36D02E3-C9F3-11CF-BFC7-444553540000}")
GUID_Slider = GUID("{A36D02E4-C9F3-11CF-BFC7-444553540000}")
GUID_POV    = GUID("{A36D02F2-C9F3-11CF-BFC7-444553540000}")

# This must match the offsets used below.
class MiniJoystickState(C.Structure):
    _fields_ = [
        ("lX", LONG),   # offset 0
        ("lY", LONG),   # offset 4
    ]

def build_minimal_xy_data_format():
    objs = (DIOBJECTDATAFORMAT * 2)()

    objs[0].pguid = C.pointer(GUID_XAxis)
    objs[0].dwOfs = 0   # offsetof(MiniJoystickState, lX)
    objs[0].dwType = DIDFT_AXIS | DIDFT_ANYINSTANCE | DIDFT_OPTIONAL
    objs[0].dwFlags = DIDOI_ASPECTPOSITION

    objs[1].pguid = C.pointer(GUID_YAxis)
    objs[1].dwOfs = 4   # offsetof(MiniJoystickState, lY)
    objs[1].dwType = DIDFT_AXIS | DIDFT_ANYINSTANCE | DIDFT_OPTIONAL
    objs[1].dwFlags = DIDOI_ASPECTPOSITION

    df = DIDATAFORMAT()
    df.dwSize = C.sizeof(DIDATAFORMAT)
    df.dwObjSize = C.sizeof(DIOBJECTDATAFORMAT)
    df.dwFlags = 0
    df.dwDataSize = C.sizeof(MiniJoystickState)
    df.dwNumObjs = 2
    df.rgodf = objs

    # Keep backing storage alive.
    df._objs_ref = objs
    df._guid_refs = [GUID_XAxis, GUID_YAxis]
    return df


def set_data_format(device, data_format=None):
    """
    Apply a DIDATAFORMAT to the device.

    If data_format is None, use a tiny X/Y demo format.
    """
    if data_format is None:
        data_format = build_minimal_xy_data_format()

    hr = device.SetDataFormat(C.byref(data_format))
    check_hr(hr, "IDirectInputDevice8W.SetDataFormat")
    return data_format


# ============================================================
# Acquire / unacquire
# ============================================================

def acquire(device):
    hr = device.Acquire()
    check_hr(hr, "IDirectInputDevice8W.Acquire")


def unacquire(device):
    hr = device.Unacquire()
    check_hr(hr, "IDirectInputDevice8W.Unacquire")


# ============================================================
# Effect enumeration
# ============================================================

_effect_enum_callbacks = []


def enum_effects(device):
    results = []

    def _cb(lpdei, pvref):
        info = lpdei.contents
        results.append({
            "guid": GUID(str(info.guid)),
            "name": info.tszName,
            "dwEffType": info.dwEffType,
            "dwStaticParams": info.dwStaticParams,
            "dwDynamicParams": info.dwDynamicParams,
        })
        return DIENUM_CONTINUE

    cb = LPDIENUMEFFECTSCALLBACKW(_cb)
    _effect_enum_callbacks.append(cb)

    hr = device.EnumEffects(cb, None, DIEFT_ALL)
    check_hr(hr, "IDirectInputDevice8W.EnumEffects")
    return results


# ============================================================
# Constant force effect creation
# ============================================================

class ConstantForceEffectHandle:
    """
    Keeps Python-owned memory alive for the lifetime of the effect.
    """

    def __init__(self, effect, dieffect, axes, directions, force):
        self.effect = effect
        self.dieffect = dieffect
        self.axes = axes
        self.directions = directions
        self.force = force

    def start(self, iterations=1, flags=0):
        hr = self.effect.Start(iterations, flags)
        check_hr(hr, "IDirectInputEffect.Start")

    def stop(self):
        hr = self.effect.Stop()
        check_hr(hr, "IDirectInputEffect.Stop")

    def download(self):
        hr = self.effect.Download()
        check_hr(hr, "IDirectInputEffect.Download")

    def unload(self):
        hr = self.effect.Unload()
        check_hr(hr, "IDirectInputEffect.Unload")

    def set_magnitude(self, magnitude, start=False):
        self.force.lMagnitude = magnitude
        flags = DIEP_TYPESPECIFICPARAMS
        if start:
            flags |= DIEP_START
        hr = self.effect.SetParameters(C.byref(self.dieffect), flags)
        check_hr(hr, "IDirectInputEffect.SetParameters")


def create_constant_force_effect(device,
                                 magnitude=5000,
                                 direction_hundredths_deg=0,
                                 duration_us=1_000_000,
                                 axes_offsets=(DIJOFS_X, DIJOFS_Y)):
    """
    Create a constant-force effect.

    direction_hundredths_deg:
        polar angle in hundredths of a degree.
        Example: 18000 means 180.00 degrees.

    duration_us:
        DirectInput uses microseconds.
    """
    axis_count = len(axes_offsets)
    if axis_count not in (1, 2):
        raise ValueError("This skeleton currently supports 1 or 2 axes.")

    axes = (DWORD * axis_count)(*axes_offsets)

    if axis_count == 1:
        directions = (LONG * 1)(direction_hundredths_deg)
    else:
        # For polar coordinates with 2 axes, second entry is reserved and should be 0.
        directions = (LONG * 2)(direction_hundredths_deg, 0)

    force = DICONSTANTFORCE()
    force.lMagnitude = magnitude

    eff = DIEFFECT()
    eff.dwSize = C.sizeof(DIEFFECT)
    eff.dwFlags = DIEFF_OBJECTOFFSETS | DIEFF_POLAR
    eff.dwDuration = duration_us
    eff.dwSamplePeriod = 0
    eff.dwGain = DI_FFNOMINALMAX
    eff.dwTriggerButton = DIEB_NOTRIGGER
    eff.dwTriggerRepeatInterval = 0
    eff.cAxes = axis_count
    eff.rgdwAxes = C.cast(axes, POINTER(DWORD))
    eff.rglDirection = C.cast(directions, POINTER(LONG))
    eff.lpEnvelope = None
    eff.cbTypeSpecificParams = C.sizeof(DICONSTANTFORCE)
    eff.lpvTypeSpecificParams = C.cast(C.pointer(force), LPVOID)
    eff.dwStartDelay = 0

    peffect = device.CreateEffect(
        C.byref(GUID_ConstantForce),
        C.byref(eff),
        None,
    )

    return ConstantForceEffectHandle(
        effect=peffect,
        dieffect=eff,
        axes=axes,
        directions=directions,
        force=force,
    )


# ============================================================
# High-level demo flow
# ============================================================

def demo():
    print("Creating DirectInput...")
    di = create_direct_input()

    print("Enumerating FF-capable game controllers...")
    devices = enum_devices(di, only_attached=True, only_force_feedback=True)
    for i, d in enumerate(devices):
        print(f"[{i}] {d['product_name']} / {d['instance_name']}")

    if not devices:
        print("No attached force-feedback game controllers found.")
        return

    print("Opening first device...")
    dev = create_device(di, devices[0]["guidInstance"])

    print("Setting cooperative level...")
    set_cooperative_level(dev)

    print("Setting data format...")
    data_format = set_data_format(dev)

    print("Acquiring device...")
    acquire(dev)

    print("Enumerating supported effects...")
    effects = enum_effects(dev)
    for e in effects:
        print("  ", e["name"], str(e["guid"]))

    print("Creating constant force effect...")
    fx = create_constant_force_effect(
        dev,
        magnitude=6000,
        direction_hundredths_deg=18000,
        duration_us=2_000_000,
        axes_offsets=(DIJOFS_X, DIJOFS_Y),
    )

    print("Downloading effect...")
    fx.download()

    print("Starting effect...")
    fx.start(iterations=1)

    print("Effect started. Sleeping 2 seconds...")
    kernel32.Sleep(2000)

    print("Stopping effect...")
    fx.stop()

    print("Unloading effect...")
    fx.unload()

    print("Unacquiring device...")
    unacquire(dev)

    print("Done.")


if __name__ == "__main__":
    demo()