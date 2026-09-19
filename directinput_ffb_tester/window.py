"""Main window of the FFB test tool."""
from __future__ import annotations

import math
import time
from typing import Optional

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from . import log
from .spec import FfbEffect, EffectSpec, ForceModel, Kinematics, Pretty, DirWord
from .views import YokeView, SliderRow, DirPad, CollapsibleGroup
from .device import DeviceSession

MAIN_EFFECTS = [e for e in FfbEffect if e is not FfbEffect.SPRING]


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("py_directinput_ffb - FFB Test Tool")
        self.resize(1280, 860)
        self.setMinimumSize(1040, 680)

        self.dev = DeviceSession()

        self._spring_dirty = False
        self._main_dirty = False
        self._last_roll = self._last_pitch = 0.0
        self._last_vel_r = self._last_vel_p = 0.0
        self._last_t = time.monotonic()
        self._frame = 0
        self._effect_started: Optional[float] = None
        self._invert = False

        self._build_widgets()
        self._wire_events()
        self.rescan_devices()
        self._update_group_enable()

        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    # ------------------------------------------------------------------ UI

    def _build_widgets(self) -> None:
        self._view = YokeView()

        self._debug = QPlainTextEdit()
        self._debug.setReadOnly(True)
        self._debug.setFont(QFont("Consolas", 9))
        self._debug.setFixedHeight(210)
        self._debug.setStyleSheet("background: #14171c; color: #c4d0c4;")

        self._rotation_range = QSpinBox()
        self._rotation_range.setRange(10, 3600)
        self._rotation_range.setValue(180)
        self._rotation_range.setSuffix(" deg")

        self._invert_view = QCheckBox("invert roll/pitch view (display only)")
        self._invert_view.setChecked(False)

        left = QWidget()
        lv = QVBoxLayout()
        lv.setContentsMargins(0, 0, 0, 0)
        strip = QHBoxLayout()
        strip.addWidget(QLabel("Device rotation range"))
        strip.addWidget(self._rotation_range)
        strip.addStretch(1)
        strip.addWidget(self._invert_view)
        lv.addLayout(strip)
        lv.addWidget(self._view, 1)
        lv.addWidget(self._debug)
        left.setLayout(lv)

        right = QScrollArea()
        right.setWidgetResizable(True)
        self._flow = QWidget()
        fv = QVBoxLayout(self._flow)
        fv.setContentsMargins(8, 8, 8, 8)

        self._cbo_device = QComboBox()
        self._cbo_device.setMinimumWidth(260)
        self._btn_rescan = QPushButton("Rescan")
        self._btn_connect = QPushButton("Connect")
        self._btn_log = QPushButton("Open log")
        self._status = QLabel("No device opened")
        self._gain = SliderRow("Device gain", 0, 10000, 10000, 100)
        gdev = CollapsibleGroup("Device", 150, collapsible=False)
        d2 = QVBoxLayout(gdev)
        row = QHBoxLayout()
        row.addWidget(self._cbo_device)
        row.addWidget(self._btn_rescan)
        row.addWidget(self._btn_connect)
        row.addWidget(self._btn_log)
        d2.addLayout(row)
        d2.addWidget(self._status)
        d2.addWidget(self._gain)
        fv.addWidget(gdev)

        self._chk_spring_on = QCheckBox("on  (centring safeguard)")
        self._chk_spring_on.setChecked(True)
        self._spring_mag = SliderRow("Positive coefficient", -10000, 10000, 8000, 100)
        self._spring_neg_coef = SliderRow("Negative coefficient", -10000, 10000, 8000, 100)
        self._spring_pos_sat = SliderRow("Positive saturation", 0, 10000, 10000, 100)
        self._spring_neg_sat = SliderRow("Negative saturation", 0, 10000, 10000, 100)
        self._spring_dead_band = SliderRow("Dead band", 0, 10000, 0, 100)
        self._spring_offx = SliderRow("Offset X", -10000, 10000, 0, 100)
        self._spring_offy = SliderRow("Offset Y", -10000, 10000, 0, 100)
        gspring = CollapsibleGroup("Spring Effect", 310, collapsible=False)
        s2 = QVBoxLayout(gspring)
        s2.addWidget(self._chk_spring_on)
        for w in (self._spring_mag, self._spring_neg_coef,
                  self._spring_pos_sat, self._spring_neg_sat,
                  self._spring_dead_band, self._spring_offx, self._spring_offy):
            s2.addWidget(w)
        fv.addWidget(gspring)

        self._chk_effect_on = QCheckBox("on")
        self._cbo_effect = QComboBox()
        for e in MAIN_EFFECTS:
            self._cbo_effect.addItem(Pretty(e), e)
        self._cbo_effect.setCurrentIndex(0)
        self._magnitude = SliderRow("Magnitude", 0, 10000, 4000, 100, vertical=True)
        self._direction = SliderRow("Direction deg", 0, 359, 270, 5, vertical=True)
        self._dir_pad = DirPad()
        self._duration = SliderRow("Duration ms", 0, 20000, 1500, 100, vertical=True)
        self._chk_infinite = QCheckBox("inf")
        self._chk_infinite.setChecked(True)
        self._duration.set_label_row_control(self._chk_infinite)
        geffect = CollapsibleGroup("Effect", 320, collapsible=False)
        e2 = QVBoxLayout(geffect)
        erow = QHBoxLayout()
        erow.addWidget(self._chk_effect_on)
        erow.addWidget(self._cbo_effect, 1)
        e2.addLayout(erow)
        for w in (self._magnitude, self._direction, self._dir_pad, self._duration):
            e2.addWidget(w)
        fv.addWidget(geffect)

        self._period = SliderRow("Period ms", 20, 5000, 1500, 20)
        self._phase = SliderRow("Phase deg", 0, 359, 0, 5)
        self._p_offset = SliderRow("Offset", -10000, 10000, 0, 100)
        self._grp_periodic = CollapsibleGroup("Periodic", 160)
        p2 = QVBoxLayout(self._grp_periodic)
        for w in (self._period, self._phase, self._p_offset):
            p2.addWidget(w)
        fv.addWidget(self._grp_periodic)

        self._ramp_start = SliderRow("Ramp start", -10000, 10000, 0, 100)
        self._ramp_end = SliderRow("Ramp end", -10000, 10000, 8000, 100)
        self._ramp_duration = SliderRow("Ramp duration ms", 0, 20000, 1500, 100)
        self._grp_ramp = CollapsibleGroup("Ramp force", 160)
        r2 = QVBoxLayout(self._grp_ramp)
        for w in (self._ramp_start, self._ramp_end, self._ramp_duration):
            r2.addWidget(w)
        fv.addWidget(self._grp_ramp)

        self._pos_coef = SliderRow("Pos coeff", -10000, 10000, 6000, 100)
        self._neg_coef = SliderRow("Neg coeff", -10000, 10000, 6000, 100)
        self._pos_sat = SliderRow("Pos sat", 0, 10000, 10000, 100)
        self._neg_sat = SliderRow("Neg sat", 0, 10000, 10000, 100)
        self._dead_band = SliderRow("Dead band", 0, 10000, 0, 100)
        self._center = SliderRow("Centre offset", -10000, 10000, 0, 100)
        self._chk_roll = QCheckBox("roll (X)")
        self._chk_roll.setChecked(True)
        self._chk_pitch = QCheckBox("pitch (Y)")
        self._chk_pitch.setChecked(True)
        self._grp_condition = CollapsibleGroup("Condition", 280)
        c2 = QVBoxLayout(self._grp_condition)
        for w in (self._pos_coef, self._neg_coef, self._pos_sat, self._neg_sat,
                  self._dead_band, self._center):
            c2.addWidget(w)
        axes_row = QHBoxLayout()
        axes_row.addWidget(self._chk_roll)
        axes_row.addWidget(self._chk_pitch)
        c2.addLayout(axes_row)
        fv.addWidget(self._grp_condition)

        self._chk_envelope = QCheckBox("use envelope")
        self._atk_level = SliderRow("Attack level", 0, 10000, 0, 100)
        self._atk_time = SliderRow("Attack ms", 0, 5000, 200, 20)
        self._fade_level = SliderRow("Fade level", 0, 10000, 0, 100)
        self._fade_time = SliderRow("Fade ms", 0, 5000, 200, 20)
        self._grp_envelope = CollapsibleGroup("Envelope (constant/ramp/periodic)", 220)
        v2 = QVBoxLayout(self._grp_envelope)
        v2.addWidget(self._chk_envelope)
        for w in (self._atk_level, self._atk_time, self._fade_level, self._fade_time):
            v2.addWidget(w)
        fv.addWidget(self._grp_envelope)
        fv.addStretch(1)

        right.setWidget(self._flow)
        split = QSplitter()
        split.addWidget(left)
        split.addWidget(right)
        split.setSizes([600, 600])
        self.setCentralWidget(split)

    def _wire_events(self) -> None:
        self._btn_rescan.clicked.connect(self.rescan_devices)
        self._btn_connect.clicked.connect(self.connect_selected)
        self._btn_log.clicked.connect(log.open_in_editor)
        self._cbo_effect.currentIndexChanged.connect(self._on_effect_change)
        self._cbo_effect.currentIndexChanged.connect(self._mark_main_dirty)
        self._chk_infinite.toggled.connect(self._on_infinite_toggle)
        self._chk_envelope.toggled.connect(self._on_envelope_toggle)
        self._chk_envelope.toggled.connect(self._mark_main_dirty)
        self._chk_roll.toggled.connect(self._mark_main_dirty)
        self._chk_pitch.toggled.connect(self._mark_main_dirty)
        for sr in (self._magnitude, self._direction, self._duration, self._period,
                   self._phase, self._p_offset, self._ramp_start, self._ramp_end,
                   self._ramp_duration, self._pos_coef, self._neg_coef, self._pos_sat,
                   self._neg_sat, self._dead_band, self._center, self._atk_level,
                   self._atk_time, self._fade_level, self._fade_time):
            sr.valueChanged.connect(self._mark_main_dirty)
        for sr in (self._spring_mag, self._spring_neg_coef,
                   self._spring_pos_sat, self._spring_neg_sat,
                   self._spring_dead_band, self._spring_offx, self._spring_offy):
            sr.valueChanged.connect(self._mark_spring_dirty)
        self._dir_pad.change_requested.connect(self._on_dir_pad)
        self._chk_spring_on.toggled.connect(self._on_spring_toggle)
        self._chk_effect_on.toggled.connect(self._on_effect_toggle)
        self._gain.valueChanged.connect(self._on_gain_change)
        self._rotation_range.valueChanged.connect(
            lambda _v: setattr(self._view, "rotation_range_deg",
                               float(self._rotation_range.value())))
        self._invert_view.toggled.connect(self._invert_view_toggled)

    # ------------------------------------------------------------- events

    def _on_dir_pad(self, deg: int) -> None:
        self._direction.set_value(deg)
        self._mark_main_dirty()

    def _mark_main_dirty(self, *_args) -> None:
        self._main_dirty = True

    def _mark_spring_dirty(self, *_args) -> None:
        self._spring_dirty = True

    def _on_effect_change(self, *_args) -> None:
        self._update_group_enable()
        self._main_dirty = True

    def _on_envelope_toggle(self, *_args) -> None:
        on = self._chk_envelope.isChecked()
        for sr in (self._atk_level, self._atk_time, self._fade_level, self._fade_time):
            sr.set_enabled(on)
        self._main_dirty = True

    def _on_gain_change(self, value: int) -> None:
        self.dev.set_device_gain(value)

    def _on_spring_toggle(self, checked: bool) -> None:
        try:
            if checked:
                self.dev.apply_spring(self._spring_spec())
                self.dev.start_spring()
                log.info("spring ON")
            else:
                self.dev.stop_spring()
                log.info("spring OFF")
        except Exception as exc:
            self._chk_spring_on.blockSignals(True)
            self._chk_spring_on.setChecked(False)
            self._chk_spring_on.blockSignals(False)
            self._show(f"spring toggle failed: {exc}")

    def _on_effect_toggle(self, checked: bool) -> None:
        try:
            if checked:
                spec = self._main_spec()
                self.dev.apply_main(spec)
                self.dev.start_main()
                self._effect_started = time.monotonic()
                log.info(f"effect ON: {spec.effect.value} dir={spec.direction_deg} "
                         f"mag={spec.magnitude}")
            else:
                self.dev.stop_main()
                self._effect_started = None
                log.info("effect OFF")
        except Exception as exc:
            self._chk_effect_on.blockSignals(True)
            self._chk_effect_on.setChecked(False)
            self._chk_effect_on.blockSignals(False)
            self._effect_started = None
            self._show(f"effect toggle failed: {exc}")

    def _show(self, msg: str) -> None:
        self._status.setText(msg)
        log.warn(msg)

    # ---------------------------------------------------------------- specs

    def _selected_effect(self) -> FfbEffect:
        return self._cbo_effect.currentData()

    def _spring_spec(self) -> EffectSpec:
        return EffectSpec(
            effect=FfbEffect.SPRING,
            positive_coefficient=self._spring_mag.value(),
            negative_coefficient=self._spring_neg_coef.value(),
            positive_saturation=self._spring_pos_sat.value(),
            negative_saturation=self._spring_neg_sat.value(),
            dead_band=self._spring_dead_band.value(),
            center_offset_x=self._spring_offx.value(),
            center_offset_y=self._spring_offy.value(),
        )

    def _main_spec(self) -> EffectSpec:
        e = self._selected_effect()
        ramp = e is FfbEffect.RAMP_FORCE
        return EffectSpec(
            effect=e,
            direction_deg=self._direction.value(),
            magnitude=self._magnitude.value(),
            duration_ms=(self._ramp_duration.value() if ramp
                         else (0 if self._chk_infinite.isChecked()
                               else self._duration.value())),
            period_ms=self._period.value(),
            phase_deg=self._phase.value(),
            periodic_offset=self._p_offset.value(),
            ramp_start=self._ramp_start.value(),
            ramp_end=self._ramp_end.value(),
            positive_coefficient=self._pos_coef.value(),
            negative_coefficient=self._neg_coef.value(),
            positive_saturation=self._pos_sat.value(),
            negative_saturation=self._neg_sat.value(),
            dead_band=self._dead_band.value(),
            center_offset_x=self._center.value(),
            center_offset_y=self._center.value(),
            apply_roll=self._chk_roll.isChecked(),
            apply_pitch=self._chk_pitch.isChecked(),
            use_envelope=self._chk_envelope.isChecked(),
            attack_level=self._atk_level.value(),
            attack_ms=self._atk_time.value(),
            fade_level=self._fade_level.value(),
            fade_ms=self._fade_time.value(),
        )

    def _update_group_enable(self) -> None:
        e = self._selected_effect()
        cond = e in (FfbEffect.SPRING, FfbEffect.DAMPER, FfbEffect.INERTIA,
                     FfbEffect.FRICTION)
        per = e in (FfbEffect.SQUARE, FfbEffect.SINE, FfbEffect.TRIANGLE,
                    FfbEffect.SAWTOOTH_UP, FfbEffect.SAWTOOTH_DOWN)
        ramp = e is FfbEffect.RAMP_FORCE
        self._grp_periodic.set_body_enabled(per)
        self._grp_periodic.set_collapsed(not per)
        self._grp_ramp.set_body_enabled(ramp)
        self._grp_ramp.set_collapsed(not ramp)
        self._grp_condition.set_body_enabled(cond)
        self._grp_condition.set_collapsed(not cond)
        self._grp_envelope.set_body_enabled(not cond)
        self._grp_envelope.set_collapsed(cond)
        self._magnitude.set_enabled(not cond)
        self._direction.set_enabled(not cond)
        self._dir_pad.set_enabled(not cond)
        self._update_duration_enable()
        self._apply_axis_availability()

    def _update_duration_enable(self) -> None:
        ramp = self._selected_effect() is FfbEffect.RAMP_FORCE
        self._chk_infinite.setEnabled(not ramp)
        self._duration.set_enabled(not ramp and not self._chk_infinite.isChecked())

    def _on_infinite_toggle(self, *_args) -> None:
        self._update_duration_enable()
        self._main_dirty = True

    def _invert_view_toggled(self, checked: bool) -> None:
        # display-only: negates the drawn arrows/position when checked
        self._invert = checked

    # ---------------------------------------------------------------- device

    def rescan_devices(self) -> None:
        self._cbo_device.clear()
        devices = self.dev.enumerate()
        for d in devices:
            self._cbo_device.addItem(d.product_name, d)
        if devices:
            self._status.setText(f"{len(devices)} FFB device(s)  |  log: {log.FilePath}")
        else:
            self._status.setText(f"no FFB devices found  |  log: {log.FilePath}")

    def connect_selected(self) -> None:
        data = self._cbo_device.currentData()
        if data is None:
            self._status.setText("pick a device first")
            return
        ok = self.dev.connect(data.guid_instance, int(self.winId()))
        if ok:
            self._status.setText(f"connected  |  axes: {self.dev.ffb_axes}")
            self.dev.set_device_gain(self._gain.value())
            self._apply_axis_availability()
            if self._chk_spring_on.isChecked():
                self.dev.apply_spring(self._spring_spec())
                self.dev.start_spring()
            if self._chk_effect_on.isChecked():
                self.dev.apply_main(self._main_spec())
                self.dev.start_main()
        else:
            self._status.setText(f"connect failed: {self.dev.last_error}")

    def _apply_axis_availability(self) -> None:
        pitch = self.dev.pitch_actuator
        self._chk_pitch.setEnabled(pitch)
        if not pitch:
            self._chk_pitch.setChecked(False)
        self._spring_offy.set_enabled(pitch)
        self._main_dirty = True
        self._spring_dirty = True

    def close_device(self) -> None:
        self.dev.disconnect()
        self._status.setText("device closed")

    # ---------------------------------------------------------------- tick

    def _tick(self) -> None:
        now = time.monotonic()
        dt = now - self._last_t
        self._last_t = now
        if dt <= 0 or dt > 0.5:
            dt = 1.0 / 60

        p = self.dev.poll()
        roll = p.roll if p.ok else self._last_roll
        pitch = p.pitch if p.ok else self._last_pitch

        vel_r = self._last_vel_r + 0.35 * ((roll - self._last_roll) / dt - self._last_vel_r)
        vel_p = self._last_vel_p + 0.35 * ((pitch - self._last_pitch) / dt - self._last_vel_p)
        acc_r = (vel_r - self._last_vel_r) / dt
        acc_p = (vel_p - self._last_vel_p) / dt
        self._last_roll, self._last_pitch = roll, pitch
        self._last_vel_r, self._last_vel_p = vel_r, vel_p

        spring_spec = self._spring_spec()
        main_spec = self._main_spec()
        self._dir_pad.set_readout(self._direction.value())

        try:
            if self._spring_dirty and self._chk_spring_on.isChecked():
                self.dev.apply_spring(spring_spec)
                self._spring_dirty = False
            if self._main_dirty and self._chk_effect_on.isChecked():
                self.dev.apply_main(main_spec)
                self._main_dirty = False
        except Exception as exc:
            if self._spring_dirty:
                self.dev.stop_spring()
                self._chk_spring_on.blockSignals(True)
                self._chk_spring_on.setChecked(False)
                self._chk_spring_on.blockSignals(False)
            if self._main_dirty:
                self.dev.stop_main()
                self._chk_effect_on.blockSignals(True)
                self._chk_effect_on.setChecked(False)
                self._chk_effect_on.blockSignals(False)
                self._effect_started = None
            self._show(str(exc))

        if (self._chk_effect_on.isChecked() and main_spec.duration_ms > 0
                and self._effect_started is not None
                and (now - self._effect_started) * 1000 > main_spec.duration_ms + 100):
            log.info(f"effect finished: {main_spec.duration_ms} ms - clearing checkbox")
            self._chk_effect_on.setChecked(False)

        t = (now - self._effect_started) if self._effect_started is not None else 0.0
        k = Kinematics(roll_pos=roll, pitch_pos=pitch, roll_vel=vel_r, pitch_vel=vel_p,
                       roll_acc=acc_r, pitch_acc=acc_p)
        f = ForceModel.evaluate_combined(
            spring_spec if self._chk_spring_on.isChecked() else None,
            main_spec if self._chk_effect_on.isChecked() else None, t, k)

        sign = -1.0 if self._invert else 1.0
        cmd_deg = float("nan")
        if self._chk_effect_on.isChecked() and not main_spec.is_condition:
            cmd_deg = (f.direction_deg if not math.isnan(f.direction_deg)
                       else float(main_spec.direction_deg))
        self._view.set_state(
            sign * roll, sign * pitch, sign * f.fx, sign * f.fy,
            cmd_deg, self.dev.connected)

        self._frame += 1
        if self._frame % 6 == 0:
            self._debug.setPlainText(
                self._build_debug(main_spec, t, p, roll, pitch, vel_r, vel_p, f))

    def _build_debug(self, s: EffectSpec, t: float, p, roll: float, pitch: float,
                     vr: float, vp: float, f: ForceModel.Result) -> str:
        lines = [
            f"DEVICE  {self.dev.device_name}   conn={self.dev.connected}  "
            f"ffb axes {self.dev.ffb_axes}",
        ]
        if self.dev.last_error:
            lines.append(f"        ! {self.dev.last_error}")
        lines += [
            f"POS     roll X {p.raw_roll:7} ({roll:6.3f})   "
            f"pitch Y {p.raw_pitch:7} ({pitch:6.3f})",
            f"        vel  r {vr:6.2f}  p {vp:6.2f} /s",
        ]
        if p.buttons:
            lines.append(f"        buttons 0x{p.buttons:X}")
        lines += [
            "",
            f"SPRING  {self._status_word(self._chk_spring_on.isChecked(), self.dev.spring_running)}   "
            f"coeff +{self._spring_mag.value()}/-{self._spring_neg_coef.value()}   "
            f"sat +{self._spring_pos_sat.value()}/-{self._spring_neg_sat.value()}   "
            f"db {self._spring_dead_band.value()}   "
            f"offX {self._spring_offx.value()}  offY {self._spring_offy.value()}",
            f"EFFECT  {self._status_word(self._chk_effect_on.isChecked(), self.dev.main_running)}   "
            f"{Pretty(s.effect)}",
        ]
        if not s.is_condition:
            lines.append(
                f"        dir {s.direction_deg:3} deg ({DirWord(s.direction_deg)})  "
                f"mag {s.magnitude}  "
                f"{'infinite' if s.duration_ms <= 0 else str(s.duration_ms) + 'ms'}  "
                f"t={t:6.2f}s")
            if s.use_envelope:
                lines.append(
                    f"        envelope  attack {s.attack_level}@{s.attack_ms}ms  "
                    f"fade {s.fade_level}@{s.fade_ms}ms")
        if s.is_periodic:
            lines.append(
                f"        period {s.period_ms}ms  phase {s.phase_deg} deg  "
                f"offset {s.periodic_offset}  wave {f.instantaneous:+6.3f}")
        if s.is_ramp:
            lines.append(f"        {s.ramp_start} -> {s.ramp_end}")
        if s.is_condition:
            lines.append(
                f"        coeff +{s.positive_coefficient}/-{s.negative_coefficient}  "
                f"sat +{s.positive_saturation}/-{s.negative_saturation}  "
                f"db {s.dead_band}  centre {s.center_offset_x}  "
                f"axes {('X' if s.apply_roll else '-')}{('Y' if s.apply_pitch else '-')}")
        lines += [
            "",
            "COMMANDED FORCE  (tool model - spring + effect; compare to the real device)",
            f"        Fx {f.fx:+8.0f}  {'right' if f.fx > 0 else 'left' if f.fx < 0 else '-'}"
            f"     Fy {f.fy:+8.0f}  "
            f"{'pull/nose-up' if f.fy > 0 else 'push/nose-down' if f.fy < 0 else '-'}",
            f"        |F| {f.magnitude:7.0f}     dir {f.direction_deg:6.1f} deg",
            "",
            f"gain {self._gain.value()}/10000",
            f"log  {log.FilePath}",
        ]
        return "\n".join(lines)

    @staticmethod
    def _status_word(checked: bool, running: bool) -> str:
        if checked and running:
            return "ON "
        if checked:
            return "on*"
        return "off"

    def closeEvent(self, event) -> None:
        self._timer.stop()
        self.dev.disconnect()
        log.info("window closing")
        super().closeEvent(event)
