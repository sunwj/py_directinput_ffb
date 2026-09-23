# FFB Test Tool — Design

Date: 2026-09-19
Status: approved (user)

## Goal

Port [barsk/FFBTestTool](https://github.com/barsk/FFBTestTool) (C#/SharpDX/WinForms)
to Python/PyQt6 on top of the existing `directinput_ffb` package, as a **new standalone
GUI tester**. The existing `py_directinput_ffb_gui_tester.py` stays untouched.

Reference semantics must be preserved; the point of the tool is to be an end-to-end
test of the device's PID implementation, so the tool must not "invent" force it does
not send.

## Scope decisions (user)

- New file/package; keep existing GUI tester.
- Full feature set (visualisation, spring safeguard, live updates, envelope, compass,
  device gain, logging, 60 Hz polling + force model).
- Library extensions permitted (additive, backward-compatible).

## Architecture

```
directinput_ffb_test_tool.py        # root launcher -> python -m directinput_ffb_tester
directinput_ffb_tester/
  __main__.py                       # app entry (QApplication, MainWindow, sys exit)
  spec.py                           # EffectSpec dataclass + ForceModel (pure math port)
  device.py                         # DeviceSession: connect/poll/2 effect slots
  views.py                          # YokeView, SliderRow, DirPad, CollapsibleGroup
  log.py                            # %LOCALAPPDATA%\py_directinput_ffb\test_tool.log
  window.py                         # MainWindow (layout, timer, wiring, debug panel)
```

### Library additions (directinput_ffb)

`dinput_definitions.py`:
- `DIPROP_FFGAIN = MAKEDIPROP(7)`, `DIPROP_AUTOCENTER = MAKEDIPROP(9)`,
  `DIPROPAUTOCENTER_OFF = 0`, `DIPROPDWORD` struct (`DIPROPHEADER diph; DWORD dwData;`),
  `SFFC_STOPALL = 0x00000020`, `DIEP_STARTDELAY = 0x00000200` (already inlined in
  `DIEP_ALLPARAMS`; promote to a named constant and use it there).

`dinput_api.py`:
- `set_device_gain(device, gain)` — SetProperty(DIPROP_FFGAIN, DIPROPDWORD).
- `set_autocenter(device, on)` — SetProperty(DIPROP_AUTOCENTER, DIPROPDWORD); caller
  catches failure (unsupported on some devices).
- `stop_all_effects(device)` — `SendForceFeedbackCommand(SFFC_STOPALL)`, used right
  after Acquire as in the reference.
- `get_device_gain(device)` — GetProperty for initial read (best-effort).

`dinput_effects.py`:
- `EffectHandle.apply(...)` — live update via `SetParameters`:
  flags = `DIEP_DURATION | DIEP_DIRECTION | DIEP_GAIN | DIEP_TYPESPECIFICPARAMS |
  DIEP_STARTDELAY | DIEP_TRIGGERBUTTON`, plus `DIEP_ENVELOPE` if an envelope is given,
  plus `DIEP_START` when the effect is running (or `start=True`). `DIEP_AXES` is
  never set (axis list is fixed at CreateEffect).
  - Optional kwargs: `duration_ms`, `direction_hundredths_deg`, `gain`, `envelope`,
    `type_specific`, `start`. Direction is applied by rewriting the kept-alive
    `directions` array in place for the handle's current basis (Cartesian for the
    tester); `dieffect.dwFlags` basis is fixed at creation.
- Envelope support in `create_constant_force_effect`, `create_ramp_force_effect`,
  `create_periodic_effect`: optional `envelope` (`DIENVELOPE` instance) pushed via
  `lpEnvelope` and kept alive on the handle. Condition effects expose no envelope
  (per DirectInput docs).
- No existing signature or behavioral change; all new parameters have defaults.

`__init__.py`: export the new helpers.

### Tester package

**spec.py** — `EffectSpec` (dataclass, reference field names; degrees/ms units) with
`IsCondition/IsPeriodic/IsRamp` and `Clone`; `ForceModel` with `Result(Fx, Fy,
Instantaneous)` (+`Magnitude`, `DirectionDeg`), `Kinematics`, `Evaluate`,
`EvaluateCombined`, per-effect formulas ported literally from the reference
(periodic waves, ramp fraction, envelope, per-axis conditions using
`-coefficient*(d-db)` clamped to saturation), plus `Pretty`, `DirWord`,
`direction_to_components` helpers. Pure Python `math`, no numpy.

**device.py** — `PollResult`, `DeviceSession`:
- `enumerate()` — `enum_devices(only_attached=True, only_force_feedback=True)`.
- `connect(guid_instance, hwnd)` — create device; `set_cooperative_level(device,
  hwnd=hwnd, exclusive=True, background=True)`; detect FFB actuator axes
  (`enum_ffb_axes_actuator_offsets`); normalise actuator axes to ±10000 via
  `set_axis_range` (best-effort per axis); `set_data_format` on the detected X/Y
  subset; `Acquire`; `SendForceFeedbackCommand(SFFC_STOPALL)`; best-effort
  `set_autocenter(False)`; read `get_device_gain`.
- `poll()` — `device.Poll()` + `GetDeviceState`; roll = first actuator offset,
  pitch = DIJOFS_Y if actuator else 0; buttons bitmask (≤32); normalised -1..1 by
  dividing by 10000; on failure re-`Acquire()` and return previous values.
- Two slots (spring + main), each `create/apply/start/stop/dispose` over the
  library; `apply` recreates the effect when the type or axis list changes
  (`dispose` + `CreateEffect`, keep running), else live-updates via
  `EffectHandle.apply(...)`. Slot state: `running`, `last_type`, `last_axes`.
- All library calls wrapped to set `last_error` and log, never raise into the timer.

**views.py**:
- `YokeView(QWidget)` — literal port of DeviceView.cs: reference frame (dashed axes +
  rings), yoke (rim arc 125–415°, cross-bar, grips, hub, receding column; pitch
  shift/scale + roll rotation via `QTransform`), force arrows (X cyan, Y purple,
  combined) with arrowheads, `|F|`/`Fx`/`Fy`/`cmd°` labels, position map (112 px
  square), axis labels, "device not connected" hint. Dark palette constants.
- `SliderRow(QWidget)` — label + `QSlider` (horizontal) + `QSpinBox` (editable),
  two-way sync, `Value` property, `SetEnabled`, `valueChanged` signal; vertical mode
  (label above bar+number) for narrow panels, `SetLabelRowControl` for the "inf"
  checkbox on the Duration row.
- `DirPad(QWidget)` — 3×3 compass: push 180° / left 90° / readout / right 270° /
  pull 0°, buttons labelled by felt direction; click sets direction.
- `CollapsibleGroup(QGroupBox)` — caption click toggles body visibility/height,
  `SetBodyEnabled` greys children without disabling the caption.

**log.py** — `Log`: append log line (timestamped) to
`%LOCALAPPDATA%\py_directinput_ffb\test_tool.log`; `Info/Warn/Error`;
`OpenInEditor()` via `os.startfile`; `FilePath` exported.

**window.py** — `MainWindow(QMainWindow)`:
- Layout: horizontal `QSplitter`. Left panel: `YokeView` (fill) + debug
  `QPlainTextEdit` (bottom, ~210 px, Consolas, dark) + top strip ("Device rotation
  range" spinbox 10..3600 default 180 + "(?)" tooltip). Right: `QScrollArea` with
  groups: Device (combo/rescan/connect/open log/gain `SliderRow`/status),
  Spring (on checkbox default checked, mag 8000 default, Offset X/Y), Effect
  (on checkbox + combo + Magnitude/Direction + DirPad + Duration + "inf" checkbox),
  Periodic, Ramp (own duration), Condition (pos/neg coeff, sat, dead band, centre,
  roll/pitch axis checkboxes), Envelope.
- Group enable logic mirrors reference: periodic/ramp/condition/envelope bodies
  enabled+collapsed per effect type; magnitude/direction/DirPad disabled for
  conditions; Duration row disabled for ramp ("inf" off).
- `QTimer` 16 ms: poll → smooth velocity (α=0.35) and acceleration; dirty flags →
  `slot.apply(...)`; auto-uncheck effect checkbox when finite duration elapsed
  (+100 ms slack, via monotonic clock); `ForceModel.EvaluateCombined`; update view
  state + `Invalidate`; debug panel every 6th frame (`BuildDebug` port).
- `closeEvent`: stop both slots, disconnect, close log.
- Uses `int(self.winId())` as the cooperative-level HWND.
- "Invert roll/pitch view" checkbox (display only, does not change what is sent) is
  included for parity with the reference.

## Semantics to preserve (verified against reference + docs)

- Direction: DirectInput "comes-from" convention; sent to the device as Cartesian
  `(sin, -cos)` (per-axis component: X→cx, Y→cy, other actuator→cx), rounded to
  ±10000; degenerate (0, -10000 at 0° etc.) is sent verbatim, never substituted.
- Felt force for the model is `(-sin, +cos)`; `DirectionDeg` of a result =
  `atan2(Fx, -Fy)` normalized to 0..360 (NaN when |F|<1).
- Conditions: one `DICONDITION` per requested actuator axis; per-axis centre offset;
  direction sent as zeroed array (Python: polar `{0,0}` default of the library —
  documented "must not be rotated"; equivalent on real drivers).
- Envelope only for constant/ramp/periodic; phase in degrees×100; period/duration
  ms→µs; effect gain fixed 10000, strength via magnitude; device gain separate.
- 1-axis device: pitch controls disabled; Y coefficient/offset UI disabled.

## Verification

- Offscreen smoke: `QT_QPA_PLATFORM=offscreen` instantiate `MainWindow`, no device
  path (status "no force-feedback devices found"), no crash.
- ForceModel parity: numeric spot-checks against the reference C# (sine at t=0 and
  t=period/4, ramp midpoint, envelope endpoints, condition saturation/deadband).
- Library additions: struct sizes vs `references/dinput.h`; flags/constants grepped
  from header; `py_compile` all files; `directinput_ffb` import + new exports.
- Real hardware: deferred to the user (no device attached in this environment).

## Out of scope

- Any change to the existing `py_directinput_ffb_gui_tester.py`.
- Autocentre toggle UI (reference dropped it; the spring effect covers it).
- Non-FFB devices / keyboard-mouse paths.
