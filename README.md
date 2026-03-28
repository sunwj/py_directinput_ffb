# py_directinput_ffb: DirectInput force-feedback Python binding

- `dinput_types.py` — base Win32 and COM type aliases, DLL loading, raw Win32 bindings
- `dinput_definitions.py` — DirectInput constants, structures, GUIDs, and COM interfaces
- `dinput_api.py` — high-level device setup helpers
- `dinput_effects.py` — constant-force effect creation and management
- `main.py` — a compact demo entry point

## Run

From this folder:

```bash
python main.py
```

## Notes

The comments are intentionally detailed because
DirectInput + `ctypes` + `comtypes` is unusually sensitive to:

- exact COM vtable order
- structure layout
- pointer lifetimes
- window-handle validity
- keeping callback objects alive


## Additional standard effect helpers

`dinput_effects.py` now includes builders for all standard DirectInput force types:

- `create_ramp_force_effect`
- `create_square_effect`
- `create_sine_effect`
- `create_triangle_effect`
- `create_sawtooth_up_effect`
- `create_sawtooth_down_effect`
- `create_spring_effect`
- `create_damper_effect`
- `create_inertia_effect`
- `create_friction_effect`

The periodic helpers share the same parameters (`magnitude`, `offset`, `phase_hundredths_deg`, `period_us`, `duration_us`).
The condition helpers share the same parameters (`positive_coefficient`, `negative_coefficient`, `positive_saturation`, `negative_saturation`, `dead_band`, `offset`, `duration_us`, and optional `per_axis`).

## Demo

`main.py` now plays each supported standard effect once. The demo first asks the device which effect GUIDs it supports, then only constructs the matching standard effects. This avoids trying to create unsupported effects on wheels or joysticks that expose only a subset of DirectInput's standard force types.
