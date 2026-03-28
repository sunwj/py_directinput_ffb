
import ctypes as C
from ctypes import wintypes as W
import math
import comtypes
from comtypes import GUID, IUnknown, COMMETHOD, POINTER, HRESULT


# ============================================================
# Basic Win32 / DirectInput types
# ============================================================

DWORD = W.DWORD
WORD = W.WORD
LONG = W.LONG
BOOL = W.BOOL
HWND = W.HWND
HINSTANCE = W.HINSTANCE
HMENU = W.HMENU
LPVOID = C.c_void_p
LPCWSTR = W.LPCWSTR
WCHAR = W.WCHAR
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

kernel32.Sleep.argtypes = [DWORD]
kernel32.Sleep.restype = None

DirectInput8Create = dinput8.DirectInput8Create
DirectInput8Create.argtypes = [
    HINSTANCE,
    DWORD,
    C.POINTER(GUID),
    C.POINTER(LPVOID),
    LPVOID,
]
DirectInput8Create.restype = HRESULT


# ============================================================
# HWND helper
# ============================================================

_hwnd_keepalive = None

def get_ffb_hwnd():
    global _hwnd_keepalive
    if _hwnd_keepalive and user32.IsWindow(_hwnd_keepalive):
        return _hwnd_keepalive

    hinst = kernel32.GetModuleHandleW(None)
    hwnd = user32.CreateWindowExW(
        0,
        "STATIC",
        "FFB_TEST",
        0,
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
# HRESULT helper
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

DI8DEVCLASS_GAMECTRL = 4

DIEDFL_ATTACHEDONLY = 0x00000001
DIEDFL_FORCEFEEDBACK = 0x00000100

DIENUM_CONTINUE = 1

DISCL_EXCLUSIVE = 0x00000001
DISCL_BACKGROUND = 0x00000008

DIEFF_CARTESIAN = 0x00000010
DIEFF_POLAR = 0x00000020
DIEFF_OBJECTOFFSETS = 0x00000002

DIEFT_ALL = 0x00000000

DI_FFNOMINALMAX = 10000
DIEB_NOTRIGGER = 0xFFFFFFFF

DIJOFS_X = 0
DIJOFS_Y = 4

DIDFT_AXIS = 0x00000003
DIDFT_ANYINSTANCE = 0x00FFFF00
DIDFT_OPTIONAL = 0x80000000
DIDFT_ALL = 0x00000000
DIDFT_FFACTUATOR = 0x01000000

DIDOI_ASPECTPOSITION = 0x00000100


# ============================================================
# GUIDs
# ============================================================

IID_IDirectInput8W = GUID("{BF798031-483A-4DA2-AA99-5D64ED369700}")
IID_IDirectInputDevice8W = GUID("{54D41081-DC15-4833-A41B-748F73A38179}")
IID_IDirectInputEffect = GUID("{E7E1F7C0-88D2-11D0-9AD0-00A0C9A06E35}")

GUID_ConstantForce = GUID("{13541C20-8E33-11D0-9AD0-00A0C9A06E35}")

GUID_XAxis = GUID("{A36D02E0-C9F3-11CF-BFC7-444553540000}")
GUID_YAxis = GUID("{A36D02E1-C9F3-11CF-BFC7-444553540000}")


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
LPDIDEVICEOBJECTINSTANCEW = POINTER(DIDEVICEOBJECTINSTANCEW)
LPDIEFFECTINFOW = POINTER(DIEFFECTINFOW)

LPDIENUMDEVICESCALLBACKW = C.WINFUNCTYPE(BOOL, LPDIDEVICEINSTANCEW, LPVOID)
LPDIENUMDEVICEOBJECTSCALLBACKW = C.WINFUNCTYPE(BOOL, LPDIDEVICEOBJECTINSTANCEW, LPVOID)
LPDIENUMEFFECTSCALLBACKW = C.WINFUNCTYPE(BOOL, LPDIEFFECTINFOW, LPVOID)


# ============================================================
# COM interfaces
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
        COMMETHOD([], HRESULT, "GetCapabilities",
                (["in", "out"], LPVOID, "lpDIDevCaps")),
        COMMETHOD([], HRESULT, "EnumObjects",
                (["in"], LPDIENUMDEVICEOBJECTSCALLBACKW, "lpCallback"),
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
# Root creation / device enumeration
# ============================================================

def create_direct_input():
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


_device_enum_callbacks = []

def enum_devices(di):
    results = []

    def _cb(lpddi, _pvref):
        inst = lpddi.contents
        results.append({
            "guidInstance": GUID(str(inst.guidInstance)),
            "guidProduct": GUID(str(inst.guidProduct)),
            "instance_name": inst.tszInstanceName,
            "product_name": inst.tszProductName,
        })
        return DIENUM_CONTINUE

    cb = LPDIENUMDEVICESCALLBACKW(_cb)
    _device_enum_callbacks.append(cb)

    hr = di.EnumDevices(
        DI8DEVCLASS_GAMECTRL,
        cb,
        None,
        DIEDFL_ATTACHEDONLY | DIEDFL_FORCEFEEDBACK,
    )
    check_hr(hr, "EnumDevices")
    return results


def create_device(di, guid_instance):
    return di.CreateDevice(C.byref(guid_instance), None)


# ============================================================
# Data format
# ============================================================

class MiniJoystickState(C.Structure):
    _fields_ = [
        ("lX", LONG),
        ("lY", LONG),
    ]


def build_minimal_xy_data_format():
    objs = (DIOBJECTDATAFORMAT * 2)()

    objs[0].pguid = C.pointer(GUID_XAxis)
    objs[0].dwOfs = 0
    objs[0].dwType = DIDFT_AXIS | DIDFT_ANYINSTANCE | DIDFT_OPTIONAL
    objs[0].dwFlags = DIDOI_ASPECTPOSITION

    objs[1].pguid = C.pointer(GUID_YAxis)
    objs[1].dwOfs = 4
    objs[1].dwType = DIDFT_AXIS | DIDFT_ANYINSTANCE | DIDFT_OPTIONAL
    objs[1].dwFlags = DIDOI_ASPECTPOSITION

    df = DIDATAFORMAT()
    df.dwSize = C.sizeof(DIDATAFORMAT)
    df.dwObjSize = C.sizeof(DIOBJECTDATAFORMAT)
    df.dwFlags = 0
    df.dwDataSize = C.sizeof(MiniJoystickState)
    df.dwNumObjs = 2
    df.rgodf = objs

    df._objs_ref = objs
    df._guid_refs = [GUID_XAxis, GUID_YAxis]
    return df


# ============================================================
# Device object enumeration: this is the key debug/fix step
# ============================================================

_object_enum_callbacks = []

def enum_ffb_actuator_offsets(device):
    actuator_offsets = []

    def _cb(lpobj, _pvref):
        obj = lpobj.contents
        obj_type = int(obj.dwType)
        print(
            f"OBJECT name={obj.tszName!r} "
            f"ofs={int(obj.dwOfs)} "
            f"type=0x{obj_type:08X} "
            f"flags=0x{int(obj.dwFlags):08X} "
            f"ff_max={int(obj.dwFFMaxForce)}"
        )

        is_axis = (obj_type & 0xFF) == DIDFT_AXIS
        is_actuator = bool(obj_type & DIDFT_FFACTUATOR)

        if is_axis and is_actuator:
            actuator_offsets.append(int(obj.dwOfs))

        return DIENUM_CONTINUE

    cb = LPDIENUMDEVICEOBJECTSCALLBACKW(_cb)
    _object_enum_callbacks.append(cb)

    hr = device.EnumObjects(cb, None, DIDFT_ALL)
    check_hr(hr, "EnumObjects")

    return tuple(actuator_offsets)


def get_effect_axes_offsets(device):
    axes_offsets = enum_ffb_actuator_offsets(device)
    print("Reported FFB actuator offsets:", axes_offsets)

    if len(axes_offsets) >= 2:
        return axes_offsets[:2]
    if len(axes_offsets) == 1:
        return axes_offsets
    print("WARNING: device did not report FFB actuators, falling back to X/Y.")
    return (DIJOFS_X, DIJOFS_Y)


# ============================================================
# Effect enumeration
# ============================================================

_effect_enum_callbacks = []

def enum_effects(device):
    results = []

    def _cb(lpdei, _pvref):
        info = lpdei.contents
        results.append({
            "guid": GUID(str(info.guid)),
            "name": info.tszName,
        })
        return DIENUM_CONTINUE

    cb = LPDIENUMEFFECTSCALLBACKW(_cb)
    _effect_enum_callbacks.append(cb)

    hr = device.EnumEffects(cb, None, DIEFT_ALL)
    check_hr(hr, "EnumEffects")
    return results


# ============================================================
# Effect wrapper
# ============================================================

class ConstantForceEffectHandle:
    def __init__(self, effect, dieffect, axes, directions, force):
        self.effect = effect
        self.dieffect = dieffect
        self.axes = axes
        self.directions = directions
        self.force = force

    def download(self):
        check_hr(self.effect.Download(), "Download")

    def start(self):
        check_hr(self.effect.Start(1, 0), "Start")

    def stop(self):
        check_hr(self.effect.Stop(), "Stop")

    def unload(self):
        check_hr(self.effect.Unload(), "Unload")


def angle_deg_to_cartesian(angle_deg: float, scale: int = 10000) -> tuple[int, int]:
    radians = math.radians(angle_deg)
    x = int(round(math.cos(radians) * scale))
    y = int(round(math.sin(radians) * scale))
    return x, y


def create_constant_force_effect_cartesian(
    device,
    *,
    magnitude: int = 5000,
    angle_deg: float = 0.0,
    duration_ms: int = 2000,
    axes_offsets: tuple[int, ...] | None = None,
) -> ConstantForceEffectHandle:
    if axes_offsets is None:
        axes_offsets = get_effect_axes_offsets(device)

    axis_count = len(axes_offsets)
    if axis_count not in (1, 2):
        raise ValueError("Only 1 or 2 actuator axes are supported in this test.")

    axes = (DWORD * axis_count)(*axes_offsets)

    if axis_count == 1:
        x, _ = angle_deg_to_cartesian(angle_deg)
        directions = (LONG * 1)(x)
    else:
        x, y = angle_deg_to_cartesian(angle_deg)
        directions = (LONG * 2)(x, y)

    force = DICONSTANTFORCE()
    force.lMagnitude = magnitude

    eff = DIEFFECT()
    eff.dwSize = C.sizeof(DIEFFECT)
    eff.dwFlags = DIEFF_OBJECTOFFSETS | DIEFF_CARTESIAN
    eff.dwDuration = duration_ms * 1000
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

    print(
        f"Creating Cartesian effect: axes={tuple(axes_offsets)} "
        f"angle={angle_deg}deg dir={tuple(directions)} magnitude={magnitude}"
    )

    return ConstantForceEffectHandle(
        effect=peffect,
        dieffect=eff,
        axes=axes,
        directions=directions,
        force=force,
    )


def create_constant_force_effect_polar(
    device,
    *,
    magnitude: int = 5000,
    angle_deg: int = 0,
    duration_ms: int = 2000,
    axes_offsets: tuple[int, ...] | None = None,
) -> ConstantForceEffectHandle:
    if axes_offsets is None:
        axes_offsets = get_effect_axes_offsets(device)

    axis_count = len(axes_offsets)
    if axis_count not in (1, 2):
        raise ValueError("Only 1 or 2 actuator axes are supported in this test.")

    axes = (DWORD * axis_count)(*axes_offsets)

    if axis_count == 1:
        directions = (LONG * 1)(angle_deg * 100)
    else:
        directions = (LONG * 2)(angle_deg * 100, 0)

    force = DICONSTANTFORCE()
    force.lMagnitude = magnitude

    eff = DIEFFECT()
    eff.dwSize = C.sizeof(DIEFFECT)
    eff.dwFlags = DIEFF_OBJECTOFFSETS | DIEFF_POLAR
    eff.dwDuration = duration_ms * 1000
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

    print(
        f"Creating Polar effect: axes={tuple(axes_offsets)} "
        f"angle={angle_deg}deg dir={tuple(directions)} magnitude={magnitude}"
    )

    return ConstantForceEffectHandle(
        effect=peffect,
        dieffect=eff,
        axes=axes,
        directions=directions,
        force=force,
    )


# ============================================================
# Demo
# ============================================================

def demo():
    print("Creating DirectInput...")
    di = create_direct_input()

    print("Enumerating FFB game controllers...")
    devices = enum_devices(di)
    for i, d in enumerate(devices):
        print(f"[{i}] {d['product_name']} / {d['instance_name']}")

    if not devices:
        print("No attached force-feedback game controllers found.")
        return

    print("Opening first device...")
    dev = create_device(di, devices[0]["guidInstance"])

    print("Setting cooperative level...")
    hwnd = get_ffb_hwnd()
    check_hr(dev.SetCooperativeLevel(hwnd, DISCL_EXCLUSIVE | DISCL_BACKGROUND), "SetCooperativeLevel")

    print("Setting data format...")
    data_format = build_minimal_xy_data_format()
    check_hr(dev.SetDataFormat(C.byref(data_format)), "SetDataFormat")

    print("Acquiring device...")
    check_hr(dev.Acquire(), "Acquire")

    print("Enumerating supported effects...")
    effects = enum_effects(dev)
    for e in effects:
        print("  ", e["name"], str(e["guid"]))

    print("\nEnumerating device objects / FFB actuators...")
    axes_offsets = get_effect_axes_offsets(dev)
    print("Using effect axes offsets:", axes_offsets)

    print("\n=== Cartesian direction test ===")
    for angle in (0, 90, 180, 270):
        print(f"\nTesting Cartesian angle {angle}°")
        fx = create_constant_force_effect_cartesian(
            dev,
            magnitude=6000,
            angle_deg=angle,
            duration_ms=1500,
            axes_offsets=axes_offsets,
        )
        fx.download()
        fx.start()
        kernel32.Sleep(1500)
        fx.stop()
        fx.unload()
        kernel32.Sleep(500)

    print("\n=== Polar direction test ===")
    for angle in (0, 90, 180, 270):
        print(f"\nTesting Polar angle {angle}°")
        fx = create_constant_force_effect_polar(
            dev,
            magnitude=6000,
            angle_deg=angle,
            duration_ms=1500,
            axes_offsets=axes_offsets,
        )
        fx.download()
        fx.start()
        kernel32.Sleep(1500)
        fx.stop()
        fx.unload()
        kernel32.Sleep(500)

    print("\nUnacquiring device...")
    check_hr(dev.Unacquire(), "Unacquire")
    print("Done.")


if __name__ == "__main__":
    demo()
