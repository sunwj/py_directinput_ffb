"""Small demo program for the ``directinput_ffb`` package.

This script opens the first attached force-feedback controller, enumerates the
standard effects the device reports, and then plays each supported effect once.

The goal of the demo is not to be physically meaningful or realistic for every
wheel/joystick. Instead, it is a compact smoke test that shows how to:

1. Create the DirectInput root object.
2. Find a force-feedback device.
3. Configure cooperative level and input data format.
4. Acquire the device.
5. Inspect the effect GUIDs the driver reports.
6. Create and briefly play each supported standard effect.

Because DirectInput devices vary widely, some devices may report only a subset
of the standard effects. The demo only tries to play effects that the current
controller says it supports.
"""

from __future__ import annotations

from typing import Callable

from directinput_ffb.dinput_types import kernel32
from directinput_ffb.dinput_definitions import (
    DIDFT_AXIS,
    DIDFT_FFACTUATOR,
    DIJOFS_X,
    DIJOFS_Y,
    GUID_ConstantForce,
    GUID_RampForce,
    GUID_Square,
    GUID_Sine,
    GUID_Triangle,
    GUID_SawtoothUp,
    GUID_SawtoothDown,
    GUID_Spring,
    GUID_Damper,
    GUID_Inertia,
    GUID_Friction,
)
from directinput_ffb import (
    create_direct_input,
    enum_device_objects,
    enum_ffb_axes_actuator_offsets,
    enum_devices,
    create_device,
    set_cooperative_level,
    set_data_format,
    acquire,
    unacquire,
    enum_effects,
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


def _guid_text(guid) -> str:
    """Return a normalized string form for GUID comparison/debug output."""
    return str(guid).lower()


def _play_once(name: str, effect, hold_ms: int = 900) -> None:
    """Download, start, wait briefly, stop, and unload one effect object."""
    print(f"Playing: {name}")
    effect.download()
    effect.start(iterations=1)
    kernel32.Sleep(hold_ms)
    effect.stop()
    effect.unload()
    kernel32.Sleep(150)


def demo() -> None:
    """Run the end-to-end smoke test for every supported standard effect."""

    print("Creating DirectInput...")
    direct_input = create_direct_input()

    print("Enumerating FF-capable game controllers...")
    devices = enum_devices(direct_input, only_attached=True, only_force_feedback=True)
    for index, device_info in enumerate(devices):
        print(f"[{index}] {device_info.product_name} / {device_info.instance_name}")

    if not devices:
        print("No attached force-feedback game controllers found.")
        return

    print("Opening first device...")
    device = create_device(direct_input, devices[0].guid_instance)

    print("Setting cooperative level...")
    hwnd = set_cooperative_level(device)

    print("Setting data format...")
    data_format = set_data_format(device)

    print("Acquiring device...")
    acquire(device)

    print("Enumerating device object information...")
    obj_infos = enum_device_objects(device, DIDFT_AXIS | DIDFT_FFACTUATOR)
    for obj_info in obj_infos: print(f'{obj_info.name}, {obj_info.offset}, {hex(obj_info.type_flags)}, is_axis: {obj_info.is_axis}, is_actuator: {obj_info.is_ff_actuator}')

    axes_offsets = enum_ffb_axes_actuator_offsets(device)

    try:
        print("Enumerating supported effects...")
        supported = enum_effects(device)
        for effect_info in supported:
            print(f"  {effect_info.name} ({effect_info.guid})")

        supported_guids = {_guid_text(effect_info.guid) for effect_info in supported}

        effect_builders: list[tuple[str, object, Callable[[], object]]] = [
            (
                "constant force",
                GUID_ConstantForce,
                lambda: create_constant_force_effect(
                    device,
                    magnitude=6000,
                    direction_hundredths_deg=18000,
                    duration_us=900_000,
                    axes_offsets=axes_offsets,
                ),
            ),
            (
                "ramp force",
                GUID_RampForce,
                lambda: create_ramp_force_effect(
                    device,
                    start_magnitude=-5000,
                    end_magnitude=7000,
                    direction_hundredths_deg=0,
                    duration_us=900_000,
                    axes_offsets=axes_offsets,
                ),
            ),
            (
                "square",
                GUID_Square,
                lambda: create_square_effect(
                    device,
                    magnitude=4500,
                    offset=0,
                    phase_hundredths_deg=0,
                    period_us=220_000,
                    direction_hundredths_deg=9000,
                    duration_us=900_000,
                    axes_offsets=axes_offsets,
                ),
            ),
            (
                "sine",
                GUID_Sine,
                lambda: create_sine_effect(
                    device,
                    magnitude=4500,
                    offset=0,
                    phase_hundredths_deg=0,
                    period_us=260_000,
                    direction_hundredths_deg=9000,
                    duration_us=900_000,
                    axes_offsets=axes_offsets,
                ),
            ),
            (
                "triangle",
                GUID_Triangle,
                lambda: create_triangle_effect(
                    device,
                    magnitude=4500,
                    offset=0,
                    phase_hundredths_deg=0,
                    period_us=260_000,
                    direction_hundredths_deg=9000,
                    duration_us=900_000,
                    axes_offsets=axes_offsets,
                ),
            ),
            (
                "sawtooth up",
                GUID_SawtoothUp,
                lambda: create_sawtooth_up_effect(
                    device,
                    magnitude=4500,
                    offset=0,
                    phase_hundredths_deg=0,
                    period_us=240_000,
                    direction_hundredths_deg=9000,
                    duration_us=900_000,
                    axes_offsets=axes_offsets,
                ),
            ),
            (
                "sawtooth down",
                GUID_SawtoothDown,
                lambda: create_sawtooth_down_effect(
                    device,
                    magnitude=4500,
                    offset=0,
                    phase_hundredths_deg=0,
                    period_us=240_000,
                    direction_hundredths_deg=9000,
                    duration_us=900_000,
                    axes_offsets=axes_offsets,
                ),
            ),
            (
                "spring",
                GUID_Spring,
                lambda: create_spring_effect(
                    device,
                    positive_coefficient=5000,
                    negative_coefficient=5000,
                    positive_saturation=10000,
                    negative_saturation=10000,
                    dead_band=300,
                    offset=0,
                    axes_offsets=axes_offsets,
                ),
            ),
            (
                "damper",
                GUID_Damper,
                lambda: create_damper_effect(
                    device,
                    positive_coefficient=3500,
                    negative_coefficient=3500,
                    positive_saturation=10000,
                    negative_saturation=10000,
                    dead_band=0,
                    offset=0,
                    axes_offsets=axes_offsets,
                ),
            ),
            (
                "inertia",
                GUID_Inertia,
                lambda: create_inertia_effect(
                    device,
                    positive_coefficient=3500,
                    negative_coefficient=3500,
                    positive_saturation=10000,
                    negative_saturation=10000,
                    dead_band=0,
                    offset=0,
                    axes_offsets=axes_offsets,
                ),
            ),
            (
                "friction",
                GUID_Friction,
                lambda: create_friction_effect(
                    device,
                    positive_coefficient=3500,
                    negative_coefficient=3500,
                    positive_saturation=10000,
                    negative_saturation=10000,
                    dead_band=0,
                    offset=0,
                    axes_offsets=axes_offsets,
                ),
            ),
        ]

        print("Playing each supported standard effect once...")
        for display_name, guid, builder in effect_builders:
            if _guid_text(guid) not in supported_guids:
                print(f"Skipping: {display_name} (not reported by device)")
                continue

            try:
                effect = builder()
                _play_once(display_name, effect)
            except Exception as exc:
                print(f"Failed while playing {display_name}: {exc}")

    finally:
        print("Unacquiring device...")
        unacquire(device)
        _ = data_format
        _ = hwnd
        print("Done.")


if __name__ == "__main__":
    demo()
