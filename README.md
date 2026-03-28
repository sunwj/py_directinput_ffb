# Refactored DirectInput force-feedback Python example

This refactor splits the original single-file script into smaller modules:

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

The refactor preserves the behaviour of the working original, but reorganizes it
for readability and maintenance. The comments are intentionally detailed because
DirectInput + `ctypes` + `comtypes` is unusually sensitive to:

- exact COM vtable order
- structure layout
- pointer lifetimes
- window-handle validity
- keeping callback objects alive
