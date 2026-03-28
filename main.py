"""Demonstration entry point for the refactored DirectInput force-feedback code.

This script keeps the top-level flow intentionally small and readable:

1. Create the DirectInput root COM object.
2. Enumerate attached force-feedback game controllers.
3. Open the first matching device.
4. Configure cooperative level and data format.
5. Acquire the device.
6. Enumerate supported effects.
7. Create and play a constant-force effect.
8. Stop and clean up.

Readers who want implementation details can then move into the smaller helper
modules without having to scan a monolithic source file first.
"""

from __future__ import annotations

from dinput_types import kernel32
from dinput_definitions import DIJOFS_X, DIJOFS_Y
from dinput_api import (
    create_direct_input,
    enum_devices,
    create_device,
    set_cooperative_level,
    set_data_format,
    acquire,
    unacquire,
    enum_effects,
)
from dinput_effects import create_constant_force_effect


def demo() -> None:
    """Run the end-to-end force-feedback demo."""

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
    set_cooperative_level(device)

    print("Setting data format...")
    data_format = set_data_format(device)

    print("Acquiring device...")
    acquire(device)

    print("Enumerating supported effects...")
    effects = enum_effects(device)
    for effect_info in effects:
        print(f"  {effect_info.name} ({effect_info.guid})")

    print("Creating constant force effect...")
    effect = create_constant_force_effect(
        device,
        magnitude=6000,
        direction_hundredths_deg=18000,
        duration_us=2_000_000,
        axes_offsets=(DIJOFS_X, DIJOFS_Y),
    )

    print("Downloading effect...")
    effect.download()

    print("Starting effect...")
    effect.start(iterations=1)

    print("Effect started. Sleeping 2 seconds...")
    kernel32.Sleep(2000)

    print("Stopping effect...")
    effect.stop()

    print("Unloading effect...")
    effect.unload()

    print("Unacquiring device...")
    unacquire(device)

    # ``data_format`` is intentionally kept referenced until the end of the
    # function so its backing arrays remain alive throughout the demo.
    _ = data_format
    print("Done.")


if __name__ == "__main__":
    demo()
