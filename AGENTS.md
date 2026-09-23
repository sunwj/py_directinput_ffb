# AGENTS.md

Pure-Python (ctypes/comtypes) binding for Microsoft DirectInput Force Feedback. **Windows only** — no Linux/macOS support.

## Run

```bash
pip install comtypes            # only hard dependency
pip install PyQt6               # only for the GUI testers
python main.py                  # CLI demo: plays each supported effect on first attached FFB device
python py_directinput_ffb_gui_tester.py   # PyQt6 GUI demo
python directinput_ffb_test_tool.py       # full FFB test tool (FFBTestTool port)
python -m unittest discover -s tests -v   # unit tests (no-device + pure-model paths)
```

- There is **no packaging metadata** (no pyproject.toml/setup.py). Always run scripts from the repo root so `import directinput_ffb` resolves.
- No tests, no CI, no linter/typecheck config. Nothing to run beyond smoke-testing the demos on real hardware.
- Requires an attached FFB-capable device (wheel/joystick); with no device, `main.py` just prints "No attached force-feedback game controllers found."

## Architecture

Import name is `directinput_ffb` (legacy name `py_directinput_ffb` is supported only as a fallback in the GUI tester, `py_directinput_ffb_gui_tester.py:96`).

- `directinput_ffb/dinput_types.py` — Win32/ctypes type aliases + loads `dinput8.dll`/`kernel32.dll`/`user32.dll` from the system (the `dlls/` folder is vendored but gitignored and unused).
- `directinput_ffb/dinput_definitions.py` — constants, GUIDs, ctypes structs, comtypes COM interfaces (largest file; mirrors the SDK headers).
- `directinput_ffb/dinput_api.py` — device creation/enumeration, cooperative level, data format, acquire, axis-range properties, device gain/autocenter/stop-all helpers.
- `directinput_ffb/dinput_effects.py` — effect factories (constant/ramp/periodic/condition) + `EffectHandle` wrappers (live `apply()`, direction rewrite, envelopes).
- `directinput_ffb_tester/` — PyQt6 FFB test tool (port of barsk/FFBTestTool): `spec.py` (EffectSpec + ForceModel), `device.py` (DeviceSession, 2 effect slots), `views.py` (YokeView/SliderRow/DirPad/CollapsibleGroup), `window.py`, `log.py`.
- `main.py`, `py_directinput_ffb_gui_tester.py`, `directinput_ffb_test_tool.py` — root-level demos.
- `references/dinput.h` and `references/ffb_example.cpp` — authoritative source for struct layouts and API semantics. Consult them before changing definitions.

## Critical gotchas

- **Native pointer lifetime is the #1 crash source.** DirectInput keeps pointers to Python-owned ctypes arrays (`DIEFFECT.cbTypeSpecificParams`, `rgdwAxes`, `rglDirection`, `DIDATAFORMAT.rgodf`). Hold them via `EffectHandle` fields (`axes`, `directions`, `type_specific`, `keepalive`) or `data_format._objs_ref`/`_guid_refs`. Do not let those objects be GC'd while the device/effect is alive. The pattern of attaching refs to the struct instance is deliberate — preserve it.
- **Call order matters:** `SetCooperativeLevel` (needs a real top-level HWND; `get_ffb_hwnd()` creates a cached hidden `STATIC` window) → `SetDataFormat` → `Acquire`. Exclusive mode (`DISCL_EXCLUSIVE`) is typically required for FFB playback.
- **`dwSize`/`cbTypeSpecificParams` must be `C.sizeof(...)`** — wrong sizes cause `E_INVALIDARG`/`DIERR_INVALIDPARAM` errors. For condition effects, `cbTypeSpecificParams` is the byte size of the whole `DICONDITION` array, not one element.
- **Direction semantics:** angles are hundredths of degrees (`9000` = 90°) in polar basis; second direction entry must be 0 for 2-axis polar; `DIEFF_CARTESIAN` uses `angle_deg_to_cartesian()` (x=sin, y=-cos scaled by 32767). For 1-axis effects `_build_axes_and_directions`/`_set_direction` force `DIEFF_CARTESIAN` and send only the x component (sin·32767; 0 at 0°/180°) so wheels steer the commanded way.
- **comtypes `[in,out]` params must NOT be typed `LPVOID`** — comtypes does `getattr(c_void_p, "_type_")` which returns `'P'` (a str) and crashes with `AttributeError: 'str' object has no attribute 'from_param'`. All `[in,out]` parameters in the COM declarations use typed `POINTER(...)` (e.g. `POINTER(DIDEVICEINSTANCEW)`); keep it that way.
- Enumeration callbacks (`EnumDevices`/`EnumObjects`/`EnumEffects`) are synchronous and results are copied into dataclasses immediately — do not hold callback objects longer than the call.
- `build_joystick_data_format(axes_offsets)` accepts a 1- or 2-axis X/Y subset; the offsets are the same `DIJOFS_*` values used by effect `rgdwAxes`.
- Always keep a reference to the returned `HWND` (from `set_cooperative_level`) — it must remain valid for the device's lifetime.
- Never run untested effects on real hardware; README has a prominent safety disclaimer (non-commercial license, use at own risk).
