
"""
PyQt6 GUI for testing DirectInput force-feedback effects with py_directinput_ffb.

This version keeps the common effect parameters shared across tabs so the
values do not change when switching between effect types. It also exposes
direction and phase in whole degrees for usability while converting them to
DirectInput's hundredths-of-a-degree units internally. Duration and period
are edited in milliseconds and converted to microseconds internally.
"""

from __future__ import annotations

import sys
import traceback
from dataclasses import dataclass
from typing import Callable, Optional

from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

# -------------------------------------------------------------------------
# Package imports
# -------------------------------------------------------------------------

try:
    from directinput_ffb.dinput_api import (
        create_direct_input,
        enum_devices,
        create_device,
        set_cooperative_level,
        set_data_format,
        acquire,
        unacquire,
        enum_effects,
    )
    from directinput_ffb.dinput_effects import (
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
    from directinput_ffb.dinput_definitions import (
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
        DIJOFS_X,
        DIJOFS_Y,
    )
except ImportError:
    from directinput_ffb.dinput_api import (
        create_direct_input,
        enum_devices,
        create_device,
        set_cooperative_level,
        set_data_format,
        acquire,
        unacquire,
        enum_effects,
    )
    from directinput_ffb.dinput_effects import (
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
    from directinput_ffb.dinput_definitions import (
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
        DIJOFS_X,
        DIJOFS_Y,
    )


@dataclass
class DeviceContext:
    di: object
    device: object
    hwnd: object
    data_format: object
    devices: list
    supported_guid_strings: set[str]


def guid_str(guid: object) -> str:
    return str(guid).lower()


def make_spinbox(
    minimum: int,
    maximum: int,
    value: int,
    step: int = 1,
    suffix: str = "",
    tooltip: str = "",
) -> QSpinBox:
    box = QSpinBox()
    box.setRange(minimum, maximum)
    box.setValue(value)
    box.setSingleStep(step)
    if suffix:
        box.setSuffix(suffix)
    if tooltip:
        box.setToolTip(tooltip)
    return box


def wrap_group(title: str, layout) -> QGroupBox:
    group = QGroupBox(title)
    group.setLayout(layout)
    return group


class SharedCommonControls(QWidget):
    """
    Common parameters shared by all effect tabs.

    These widgets live once in the main window, not once per tab. That keeps
    their values stable when switching tabs.
    """

    def __init__(self) -> None:
        super().__init__()

        self.axis_mode = QComboBox()
        self.axis_mode.addItems([
            "1 axis (X)",
            "2 axes (X,Y)",
        ])
        self.axis_mode.setToolTip(
            "Choose whether the effect should be created on only the X axis "
            "or on both X and Y."
        )

        # User edits whole degrees; DirectInput receives hundredths of degrees.
        self.direction_deg = make_spinbox(
            0,
            359,
            0,
            step=1,
            suffix=" °",
            tooltip="Effect direction in whole degrees. Converted internally to DirectInput units.",
        )

        # User edits milliseconds; DirectInput receives microseconds.
        self.duration_ms = make_spinbox(
            1,
            2_147_483,
            1000,
            step=10,
            suffix=" ms",
            tooltip="Effect duration in milliseconds. Converted internally to microseconds.",
        )

        self.infinite_duration = QCheckBox("Infinite duration")
        self.infinite_duration.setChecked(False)
        self.infinite_duration.toggled.connect(self._sync_duration_enabled)
        self._sync_duration_enabled()

        layout = QFormLayout()
        layout.addRow("Axes", self.axis_mode)
        layout.addRow("Direction", self.direction_deg)

        duration_row = QHBoxLayout()
        duration_row.addWidget(self.duration_ms)
        duration_row.addWidget(self.infinite_duration)
        duration_holder = QWidget()
        duration_holder.setLayout(duration_row)
        layout.addRow("Duration", duration_holder)
        self.setLayout(layout)

    def _sync_duration_enabled(self) -> None:
        self.duration_ms.setEnabled(not self.infinite_duration.isChecked())

    def axes_offsets(self) -> tuple[int, ...]:
        return (DIJOFS_X,) if self.axis_mode.currentIndex() == 0 else (DIJOFS_X, DIJOFS_Y)

    def direction_hundredths_deg(self) -> int:
        return int(self.direction_deg.value()) * 100

    def duration_us(self) -> int:
        if self.infinite_duration.isChecked():
            return 0xFFFFFFFF
        return int(self.duration_ms.value()) * 1000


class ConditionAxisControls(QWidget):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.offset = make_spinbox(-10000, 10000, 0, step=100)
        self.positive_coefficient = make_spinbox(-10000, 10000, 5000, step=100)
        self.negative_coefficient = make_spinbox(-10000, 10000, 5000, step=100)
        self.positive_saturation = make_spinbox(0, 10000, 10000, step=100)
        self.negative_saturation = make_spinbox(0, 10000, 10000, step=100)
        self.dead_band = make_spinbox(0, 10000, 0, step=100)

        form = QFormLayout()
        form.addRow("Offset", self.offset)
        form.addRow("+ Coefficient", self.positive_coefficient)
        form.addRow("- Coefficient", self.negative_coefficient)
        form.addRow("+ Saturation", self.positive_saturation)
        form.addRow("- Saturation", self.negative_saturation)
        form.addRow("Dead band", self.dead_band)
        self.setLayout(form)
        self.setObjectName(title)

    def as_dict(self) -> dict[str, int]:
        return {
            "offset": int(self.offset.value()),
            "positive_coefficient": int(self.positive_coefficient.value()),
            "negative_coefficient": int(self.negative_coefficient.value()),
            "positive_saturation": int(self.positive_saturation.value()),
            "negative_saturation": int(self.negative_saturation.value()),
            "dead_band": int(self.dead_band.value()),
        }


class EffectTab(QWidget):
    effect_name = "Effect"

    def __init__(self, window: "MainWindow", supported_guid: object) -> None:
        super().__init__()
        self.window = window
        self.supported_guid = supported_guid
        self.current_effect: Optional[EffectHandle] = None

        self.status_label = QLabel("Not checked yet")
        self.status_label.setStyleSheet("font-weight: bold;")

        self.start_button = QPushButton("Start / Restart")
        self.stop_button = QPushButton("Stop")
        self.start_button.clicked.connect(self.start_effect)
        self.stop_button.clicked.connect(self.stop_effect)

    @property
    def common(self) -> SharedCommonControls:
        return self.window.common_controls

    def is_supported(self) -> bool:
        ctx = self.window.ctx
        if ctx is None:
            return False
        return guid_str(self.supported_guid) in ctx.supported_guid_strings

    def refresh_support_state(self) -> None:
        ctx = self.window.ctx
        if ctx is None:
            self.status_label.setText("Open a device first.")
            self.status_label.setStyleSheet("font-weight: bold; color: #a0a0a0;")
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            return

        if self.is_supported():
            self.status_label.setText(f"{self.effect_name}: supported by current device")
            self.status_label.setStyleSheet("font-weight: bold; color: #2e8b57;")
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(True)
        else:
            self.status_label.setText(f"{self.effect_name}: not reported as supported")
            self.status_label.setStyleSheet("font-weight: bold; color: #cc6600;")
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(False)

    def create_effect(self) -> EffectHandle:
        raise NotImplementedError

    def start_effect(self) -> None:
        try:
            self.window.ensure_device_ready()
            self.window.stop_active_effect()
            effect = self.create_effect()
            effect.download()
            effect.start(iterations=1)
            self.current_effect = effect
            self.window.active_tab = self
            self.window.log(f"Started {self.effect_name}")
        except Exception as exc:
            self.window.show_exception(f"Failed to start {self.effect_name}", exc)

    def stop_effect(self) -> None:
        try:
            if self.current_effect is not None:
                try:
                    self.current_effect.stop()
                finally:
                    try:
                        self.current_effect.unload()
                    finally:
                        self.current_effect = None
                self.window.log(f"Stopped {self.effect_name}")
            if self.window.active_tab is self:
                self.window.active_tab = None
        except Exception as exc:
            self.window.show_exception(f"Failed to stop {self.effect_name}", exc)


class ConstantForceTab(EffectTab):
    effect_name = "Constant Force"

    def __init__(self, window: "MainWindow") -> None:
        super().__init__(window, GUID_ConstantForce)
        self.magnitude = make_spinbox(-10000, 10000, 5000, step=100)

        params = QFormLayout()
        params.addRow("Magnitude", self.magnitude)

        layout = QVBoxLayout()
        layout.addWidget(self.status_label)
        layout.addWidget(wrap_group("Constant force parameters", params))
        buttons = QHBoxLayout()
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.stop_button)
        layout.addLayout(buttons)
        layout.addStretch()
        self.setLayout(layout)

    def create_effect(self) -> ConstantForceEffectHandle:
        return create_constant_force_effect(
            self.window.ctx.device,
            magnitude=int(self.magnitude.value()),
            direction_hundredths_deg=self.common.direction_hundredths_deg(),
            duration_us=self.common.duration_us(),
            axes_offsets=self.common.axes_offsets(),
        )


class RampForceTab(EffectTab):
    effect_name = "Ramp Force"

    def __init__(self, window: "MainWindow") -> None:
        super().__init__(window, GUID_RampForce)
        self.start_magnitude = make_spinbox(-10000, 10000, -2000, step=100)
        self.end_magnitude = make_spinbox(-10000, 10000, 6000, step=100)

        params = QFormLayout()
        params.addRow("Start magnitude", self.start_magnitude)
        params.addRow("End magnitude", self.end_magnitude)

        layout = QVBoxLayout()
        layout.addWidget(self.status_label)
        layout.addWidget(wrap_group("Ramp parameters", params))
        buttons = QHBoxLayout()
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.stop_button)
        layout.addLayout(buttons)
        layout.addStretch()
        self.setLayout(layout)

    def create_effect(self) -> RampForceEffectHandle:
        if self.common.infinite_duration.isChecked():
            raise ValueError("Ramp force requires a finite duration.")
        return create_ramp_force_effect(
            self.window.ctx.device,
            start_magnitude=int(self.start_magnitude.value()),
            end_magnitude=int(self.end_magnitude.value()),
            direction_hundredths_deg=self.common.direction_hundredths_deg(),
            duration_us=self.common.duration_us(),
            axes_offsets=self.common.axes_offsets(),
        )


class PeriodicEffectTab(EffectTab):
    def __init__(
        self,
        window: "MainWindow",
        *,
        effect_name: str,
        supported_guid: object,
        factory: Callable[..., PeriodicEffectHandle],
    ) -> None:
        super().__init__(window, supported_guid)
        self.effect_name = effect_name
        self.factory = factory

        self.magnitude = make_spinbox(0, 10000, 5000, step=100)
        self.offset = make_spinbox(-10000, 10000, 0, step=100)
        # Whole degrees in UI; converted to hundredths internally.
        self.phase_deg = make_spinbox(
            0, 359, 0, step=1, suffix=" °",
            tooltip="Phase in whole degrees. Converted internally to DirectInput units.",
        )
        # Milliseconds in UI; converted to microseconds internally.
        self.period_ms = make_spinbox(
            1, 10_000, 250, step=10, suffix=" ms",
            tooltip="Period in milliseconds. Converted internally to microseconds.",
        )

        params = QFormLayout()
        params.addRow("Magnitude", self.magnitude)
        params.addRow("Offset", self.offset)
        params.addRow("Phase", self.phase_deg)
        params.addRow("Period", self.period_ms)

        layout = QVBoxLayout()
        layout.addWidget(self.status_label)
        layout.addWidget(wrap_group(f"{self.effect_name} parameters", params))
        buttons = QHBoxLayout()
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.stop_button)
        layout.addLayout(buttons)
        layout.addStretch()
        self.setLayout(layout)

    def create_effect(self) -> PeriodicEffectHandle:
        return self.factory(
            self.window.ctx.device,
            magnitude=int(self.magnitude.value()),
            offset=int(self.offset.value()),
            phase_hundredths_deg=int(self.phase_deg.value()) * 100,
            period_us=int(self.period_ms.value()) * 1000,
            direction_hundredths_deg=self.common.direction_hundredths_deg(),
            duration_us=self.common.duration_us(),
            axes_offsets=self.common.axes_offsets(),
        )


class ConditionEffectTab(EffectTab):
    def __init__(
        self,
        window: "MainWindow",
        *,
        effect_name: str,
        supported_guid: object,
        factory: Callable[..., ConditionEffectHandle],
    ) -> None:
        super().__init__(window, supported_guid)
        self.effect_name = effect_name
        self.factory = factory

        self.axis1 = ConditionAxisControls("Axis 1")
        self.axis2 = ConditionAxisControls("Axis 2")

        self.copy_axis1_to_axis2 = QCheckBox("Copy axis 1 values to axis 2")
        self.copy_axis1_to_axis2.setChecked(True)
        self.copy_axis1_to_axis2.toggled.connect(self._sync_axis2_enabled)
        self.common.axis_mode.currentIndexChanged.connect(self._sync_axis2_enabled)
        self._sync_axis2_enabled()

        axis_layout = QGridLayout()
        axis_layout.addWidget(wrap_group("Axis 1 condition", self.axis1.layout()), 0, 0)
        axis_layout.addWidget(wrap_group("Axis 2 condition", self.axis2.layout()), 0, 1)

        layout = QVBoxLayout()
        layout.addWidget(self.status_label)
        layout.addWidget(self.copy_axis1_to_axis2)
        layout.addLayout(axis_layout)
        buttons = QHBoxLayout()
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.stop_button)
        layout.addLayout(buttons)
        layout.addStretch()
        self.setLayout(layout)

    def _sync_axis2_enabled(self) -> None:
        use_two_axes = self.common.axis_mode.currentIndex() == 1
        if not use_two_axes:
            self.axis2.setEnabled(False)
            return
        self.axis2.setEnabled(not self.copy_axis1_to_axis2.isChecked())

    def create_effect(self) -> ConditionEffectHandle:
        axis1 = self.axis1.as_dict()
        if self.common.axis_mode.currentIndex() == 0:
            per_axis = [axis1]
        else:
            axis2 = axis1 if self.copy_axis1_to_axis2.isChecked() else self.axis2.as_dict()
            per_axis = [axis1, axis2]

        return self.factory(
            self.window.ctx.device,
            direction_hundredths_deg=self.common.direction_hundredths_deg(),
            duration_us=self.common.duration_us(),
            axes_offsets=self.common.axes_offsets(),
            per_axis=per_axis,
        )


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("py_directinput_ffb - Effect Tester")
        self.resize(1200, 920)

        self.ctx: Optional[DeviceContext] = None
        self.active_tab: Optional[EffectTab] = None

        self.common_controls = SharedCommonControls()

        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(500)

        self.refresh_button = QPushButton("Refresh devices")
        self.open_button = QPushButton("Open selected device")
        self.close_button = QPushButton("Close device")

        self.refresh_button.clicked.connect(self.refresh_devices)
        self.open_button.clicked.connect(self.open_selected_device)
        self.close_button.clicked.connect(self.close_device)

        self.device_status = QLabel("No device opened")
        self.device_status.setStyleSheet("font-weight: bold;")

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)

        self.tabs = QTabWidget()
        self.effect_tabs: list[EffectTab] = [
            ConstantForceTab(self),
            RampForceTab(self),
            PeriodicEffectTab(self, effect_name="Square", supported_guid=GUID_Square, factory=create_square_effect),
            PeriodicEffectTab(self, effect_name="Sine", supported_guid=GUID_Sine, factory=create_sine_effect),
            PeriodicEffectTab(self, effect_name="Triangle", supported_guid=GUID_Triangle, factory=create_triangle_effect),
            PeriodicEffectTab(self, effect_name="Sawtooth Up", supported_guid=GUID_SawtoothUp, factory=create_sawtooth_up_effect),
            PeriodicEffectTab(self, effect_name="Sawtooth Down", supported_guid=GUID_SawtoothDown, factory=create_sawtooth_down_effect),
            ConditionEffectTab(self, effect_name="Spring", supported_guid=GUID_Spring, factory=create_spring_effect),
            ConditionEffectTab(self, effect_name="Damper", supported_guid=GUID_Damper, factory=create_damper_effect),
            ConditionEffectTab(self, effect_name="Inertia", supported_guid=GUID_Inertia, factory=create_inertia_effect),
            ConditionEffectTab(self, effect_name="Friction", supported_guid=GUID_Friction, factory=create_friction_effect),
        ]
        for tab in self.effect_tabs:
            self.tabs.addTab(tab, tab.effect_name)

        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Device"))
        top_bar.addWidget(self.device_combo, 1)
        top_bar.addWidget(self.refresh_button)
        top_bar.addWidget(self.open_button)
        top_bar.addWidget(self.close_button)

        root = QVBoxLayout()
        root.addLayout(top_bar)
        root.addWidget(self.device_status)
        root.addWidget(wrap_group("Common parameters", self.common_controls.layout()))
        root.addWidget(self.tabs, 1)
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout()
        log_layout.addWidget(self.log_view)
        log_group.setLayout(log_layout)
        root.addWidget(log_group)

        container = QWidget()
        container.setLayout(root)
        self.setCentralWidget(container)

        self.refresh_devices()
        self.refresh_tab_support()

    def log(self, text: str) -> None:
        self.log_view.appendPlainText(text)

    def show_exception(self, title: str, exc: Exception) -> None:
        self.log(f"{title}: {exc}")
        self.log(traceback.format_exc())
        QMessageBox.critical(self, title, f"{exc}\n\nSee the log pane for details.")

    def refresh_devices(self) -> None:
        self.device_combo.clear()
        self._enumerated_devices = []
        try:
            di = create_direct_input()
            devices = enum_devices(di, only_attached=True, only_force_feedback=True)
            self._enumerated_devices = devices
            for dev in devices:
                label = f"{dev.product_name} / {dev.instance_name}"
                self.device_combo.addItem(label, dev)
            if not devices:
                self.device_combo.addItem("No force-feedback devices found", None)
            self.log(f"Found {len(devices)} force-feedback device(s)")
        except Exception as exc:
            self.show_exception("Failed to enumerate devices", exc)

    def open_selected_device(self) -> None:
        self.close_device()
        data = self.device_combo.currentData()
        if data is None:
            QMessageBox.warning(self, "No device", "No force-feedback device is selected.")
            return

        try:
            di = create_direct_input()
            devices = enum_devices(di, only_attached=True, only_force_feedback=True)
            selected = data

            # Support either object-style or dict-style device items.
            if hasattr(selected, "guid_instance"):
                guid_instance = selected.guid_instance
                product_name = selected.product_name
                instance_name = selected.instance_name
            else:
                guid_instance = selected["guidInstance"]
                product_name = selected["product_name"]
                instance_name = selected["instance_name"]

            device = create_device(di, guid_instance)
            hwnd = set_cooperative_level(device, exclusive=True, background=True)
            data_format = set_data_format(device)
            acquire(device)

            effects = enum_effects(device)
            supported_guid_strings = {guid_str(e.guid if hasattr(e, "guid") else e["guid"]) for e in effects}

            self.ctx = DeviceContext(
                di=di,
                device=device,
                hwnd=hwnd,
                data_format=data_format,
                devices=devices,
                supported_guid_strings=supported_guid_strings,
            )

            self.device_status.setText(
                f"Opened: {product_name} / {instance_name} "
                f"({len(effects)} effect type(s) reported)"
            )
            self.device_status.setStyleSheet("font-weight: bold; color: #2e8b57;")
            self.log(f"Opened device: {product_name} / {instance_name}")
            for eff in effects:
                name = eff.name if hasattr(eff, "name") else eff["name"]
                guid = eff.guid if hasattr(eff, "guid") else eff["guid"]
                self.log(f"  Supports: {name} ({guid})")

            self.refresh_tab_support()
        except Exception as exc:
            self.ctx = None
            self.device_status.setText("Failed to open device")
            self.device_status.setStyleSheet("font-weight: bold; color: #b22222;")
            self.refresh_tab_support()
            self.show_exception("Failed to open selected device", exc)

    def ensure_device_ready(self) -> None:
        if self.ctx is None:
            raise RuntimeError("Open a force-feedback device first.")

    def stop_active_effect(self) -> None:
        if self.active_tab is not None:
            self.active_tab.stop_effect()
            self.active_tab = None

    def close_device(self) -> None:
        self.stop_active_effect()
        if self.ctx is None:
            self.refresh_tab_support()
            return

        try:
            unacquire(self.ctx.device)
        except Exception:
            pass

        self.ctx = None
        self.device_status.setText("No device opened")
        self.device_status.setStyleSheet("font-weight: bold;")
        self.log("Closed device")
        self.refresh_tab_support()

    def refresh_tab_support(self) -> None:
        for tab in self.effect_tabs:
            tab.refresh_support_state()

    def closeEvent(self, event) -> None:  # noqa: N802
        self.close_device()
        super().closeEvent(event)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("py_directinput_ffb Effect Tester")
    win = MainWindow()
    win.show()

    QMessageBox.information(
        win,
        "Safety warning",
        "Force-feedback devices can move suddenly and strongly.\n\n"
        "Start with low values and keep hands clear while testing.\n\n"
        "Use at your own risk.",
    )
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
