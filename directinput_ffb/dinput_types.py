"""Low-level Win32, ctypes, and COM type aliases used by the DirectInput wrapper.

This module intentionally contains *only* foundational types and loaded DLL handles.
Keeping these definitions in one place makes the rest of the project easier to read:

- structure definitions can import a stable type vocabulary
- COM interface declarations can refer to the same POINTER/GUID aliases everywhere
- Win32 API bindings live next to the DLL objects they belong to

The code in this project uses ``ctypes`` for structure layout and raw Win32 bindings,
and ``comtypes`` for COM interface definitions.
"""

from __future__ import annotations

import ctypes as C
from ctypes import wintypes as W

import comtypes
from comtypes import GUID, IUnknown, COMMETHOD, POINTER, HRESULT

# ---------------------------------------------------------------------------
# Common Win32 scalar aliases
# ---------------------------------------------------------------------------
#
# DirectInput headers are written in terms of Win32 typedefs such as DWORD,
# LONG, HWND, etc. Mirroring those names in Python makes the mapping from the
# C SDK to this wrapper much easier to follow.

DWORD = W.DWORD
WORD = W.WORD
LONG = W.LONG
ULONG = W.ULONG
UINT = W.UINT
BOOL = W.BOOL
HWND = W.HWND
HINSTANCE = W.HINSTANCE
HMENU = W.HMENU
HANDLE = W.HANDLE
LPVOID = C.c_void_p
LPCVOID = C.c_void_p
LPCWSTR = W.LPCWSTR
WCHAR = W.WCHAR
CHAR = C.c_char
MAX_PATH = 260

# ``REFGUID`` in C is effectively ``const GUID*``.
REFGUID = POINTER(GUID)
LPGUID = POINTER(GUID)

# ---------------------------------------------------------------------------
# Loaded DLL handles
# ---------------------------------------------------------------------------
#
# These are shared by the rest of the package. Keeping them here avoids each
# module loading the same DLL independently.

dinput8 = C.WinDLL("dinput8.dll")
kernel32 = C.WinDLL("kernel32.dll")
user32 = C.WinDLL("user32.dll")

# ---------------------------------------------------------------------------
# Frequently used Win32 function prototypes
# ---------------------------------------------------------------------------
#
# By default, ctypes assumes a generic ``int`` return type. That is dangerous
# for pointer-returning functions on 64-bit Python, so we always spell out the
# argument and return types explicitly.

user32.CreateWindowExW.argtypes = [
    DWORD, LPCWSTR, LPCWSTR, DWORD,
    C.c_int, C.c_int, C.c_int, C.c_int,
    HWND, HMENU, HINSTANCE, LPVOID,
]
user32.CreateWindowExW.restype = HWND

user32.IsWindow.argtypes = [HWND]
user32.IsWindow.restype = BOOL

kernel32.GetModuleHandleW.argtypes = [LPCWSTR]
kernel32.GetModuleHandleW.restype = HINSTANCE

kernel32.Sleep.argtypes = [DWORD]
kernel32.Sleep.restype = None

# ``DirectInput8Create`` is the top-level factory exported by dinput8.dll.
DirectInput8Create = dinput8.DirectInput8Create
DirectInput8Create.argtypes = [
    HINSTANCE,
    DWORD,
    C.POINTER(GUID),
    C.POINTER(LPVOID),
    LPVOID,
]
DirectInput8Create.restype = HRESULT

__all__ = [
    "C",
    "W",
    "GUID",
    "IUnknown",
    "COMMETHOD",
    "POINTER",
    "HRESULT",
    "DWORD",
    "WORD",
    "LONG",
    "ULONG",
    "UINT",
    "BOOL",
    "HWND",
    "HINSTANCE",
    "HMENU",
    "HANDLE",
    "LPVOID",
    "LPCVOID",
    "LPCWSTR",
    "WCHAR",
    "CHAR",
    "MAX_PATH",
    "REFGUID",
    "LPGUID",
    "dinput8",
    "kernel32",
    "user32",
    "DirectInput8Create",
]
