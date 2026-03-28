# <img src="icon/logo.jpg" alt="py_directinput_ffb" width="128"/> py_directinput_ffb

A Python binding for **DirectInput Force Feedback (FFB)** using `ctypes` and `comtypes`.

`py_directinput_ffb` provides low-level access to Microsoft DirectInput's force feedback system, allowing Python programs to create, control, and combine force effects on supported USB HID devices such as **joysticks, racing wheels, and other FFB-capable controllers**.

---

## ⚠️ Safety Disclaimer

This software provides direct control over force feedback (FFB) devices such as joysticks, racing wheels, and other haptic hardware.

⚠️ **Use at your own risk.**

Improper use of force feedback effects may result in:
- Physical damage to hardware devices
- Excessive wear or overheating of motors
- Unexpected or strong mechanical movements
- Personal injury (e.g., hand or finger strain, impact)

By using this software, you acknowledge that:

- You are solely responsible for how the software is used
- You understand the risks associated with force feedback systems
- You will take appropriate precautions when testing or running effects
- The author is **not responsible for any damage, injury, or loss** resulting from use of this software

### Recommendations

- Start with low force magnitudes
- Avoid continuous high-force effects
- Keep hands clear during testing
- Use devices in a stable and safe environment
- Test new effects incrementally

If you are unsure about the behavior of an effect, **do not run it on real hardware**.

---

## ✨ Features

- 🎮 Direct access to **DirectInput 8 Force Feedback API**
- 🧩 Pure Python implementation (no C/C++ extension required)
- ⚡ Support for a wide range of force effects:
  - Constant force
  - Ramp force
  - Periodic forces:
    - Sine
    - Square
    - Triangle
    - Sawtooth (up/down)
  - Condition forces:
    - Spring
    - Damper
    - Inertia
    - Friction
- 🔍 Device enumeration and capability inspection
- 🎯 Fine-grained control over:
  - Direction
  - Magnitude
  - Duration
  - Gain
  - Axis mapping
- 🧠 Explicit control over DirectInput structures and memory layout

---

## 📦 Installation

This package is designed to run on **Windows only**, as it depends on DirectInput.

```bash
git clone https://github.com/your-repo/py_directinput_ffb.git
cd py_directinput_ffb
```

---

## 🖥️ Requirements

- Windows (DirectInput is part of DirectX)
- Python 3.8+
- `comtypes`

Install dependency:

```bash
pip install comtypes
```

---

## 🚀 Quick Example

```python
from directinput_ffb.dinput_api import create_direct_input, enum_devices, create_device
from directinput_ffb.dinput_effects import create_constant_force_effect

# Initialize DirectInput
di = create_direct_input()

# Find force feedback devices
devices = enum_devices(di, only_attached=True, only_force_feedback=True)

# Open first device
device = create_device(di, devices[0]["guidInstance"])

# Setup device
device.SetDataFormat(...)
device.SetCooperativeLevel(...)
device.Acquire()

# Create a constant force effect
effect = create_constant_force_effect(
    device,
    magnitude=6000,
    direction_hundredths_deg=18000,
    duration_us=2_000_000,
)

effect.download()
effect.start()

# Stop after use
effect.stop()
effect.unload()
device.Unacquire()
```

---

## 🎛️ Supported Force Effects

### Constant Force
Applies a steady force in a given direction.

### Ramp Force
Linearly transitions from one magnitude to another.

### Periodic Effects
Oscillating forces:
- Sine
- Square
- Triangle
- Sawtooth Up / Down

### Condition Effects
Physics-like constraints:
- Spring (centering force)
- Damper (resistance to velocity)
- Inertia (mass simulation)
- Friction (static resistance)

---

## 🧱 Architecture Overview

```
directinput_ffb/
│
├── dinput_types.py        # Low-level Win32 + ctypes types
├── dinput_definitions.py  # DirectInput constants, GUIDs, structures, COM interfaces
├── dinput_api.py          # Device management and setup
├── dinput_effects.py      # Force effect creation and control
├── main.py                # Demo: play supported effects
```

### Key Concepts

- **COM Interfaces** are defined using `comtypes`
- **Structures** mirror DirectInput C structs exactly
- **Memory ownership is explicit** (important for stability)
- **Callbacks are retained** to prevent garbage collection

---

## ⚠️ Important Notes

- ✔ Devices must support **Force Feedback (FFB)**  
- ✔ Cooperative level must be set **before Acquire()**  
- ✔ Effects typically require **exclusive mode**  
- ✔ Many errors are caused by:
  - invalid data formats
  - incorrect structure sizes (`dwSize`)
  - invalid window handles (`HWND`)

---

## 🧪 Demo

Run the built-in demo to test all supported effects:

```bash
python main.py
```

This will:
- Detect a compatible FFB device
- Enumerate supported effects
- Play each effect once

---

## 🎯 Use Cases

- Simulation (flight, racing, robotics)
- Game prototyping
- Hardware testing / validation
- Research on haptic feedback systems

---

## 📚 References

- Microsoft DirectInput documentation  
- DirectX SDK headers (`dinput.h`)
- HID PID (Physical Interface Device) standard

---

## 📜 License

This project is licensed for **non-commercial use only**.

Commercial use requires a separate license.  
Please contact the author for licensing options.

---

## 🤝 Contributing

Contributions are welcome!  
Feel free to open issues or submit pull requests.

---

## 💡 Final Note

This library intentionally stays **close to the native DirectInput API**, exposing its power while remaining usable from Python.  
It is designed for users who need **precise, low-level control over force feedback devices**.