"""directinput_ffb: a small pure-Python DirectInput force-feedback binding.

This package wraps the parts of DirectInput 8 needed to enumerate
force-feedback devices, acquire them, inspect their supported effects,
and create standard force-feedback effects through ctypes/comtypes.

The package is intentionally split into layers:
- dinput_types: raw Win32 and COM aliases plus DLL loading
- dinput_definitions: DirectInput constants, structures, and interfaces
- dinput_api: device setup and enumeration helpers
- dinput_effects: effect-construction and effect-lifetime helpers
"""

from .dinput_api import (
    check_hr,
    create_direct_input,
    enum_devices,
    create_device,
    set_cooperative_level,
    set_data_format,
    acquire,
    unacquire,
    enum_effects,
    enum_device_objects,
    enum_ffb_axes_actuator_offsets,
    get_axis_logical_range,
    get_axis_physical_range,
    set_axis_range,
)
from .dinput_effects import (
    EffectHandle,
    ConstantForceEffectHandle,
    RampForceEffectHandle,
    PeriodicEffectHandle,
    ConditionEffectHandle,
    create_constant_force_effect,
    create_ramp_force_effect,
    create_square_effect,
    create_sine_effect,
    create_triangle_effect,
    create_sawtooth_up_effect,
    create_sawtooth_down_effect,
    create_spring_effect,
    create_damper_effect,
    create_inertia_effect,
    create_friction_effect,
)

__all__ = [name for name in globals() if not name.startswith('_')]
