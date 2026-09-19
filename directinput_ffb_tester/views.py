"""Qt widgets: yoke visualisation, slider rows, compass pad, collapsible groups."""
from __future__ import annotations

import math

from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QTransform
from PyQt6.QtWidgets import (
    QGroupBox,
    QGridLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QWidget,
)

BG = QColor(0x12, 0x15, 0x1a)
GRID = QColor(0x27, 0x2c, 0x36)
YOKE = QColor(0xcc, 0xd2, 0xdc)
YOKE_DIM = QColor(0x6a, 0x72, 0x82)
HUB = QColor(0x9a, 0xa4, 0xb2)
FX_COL = QColor(0x22, 0xd3, 0xee)
FY_COL = QColor(0xa7, 0x8b, 0xfa)
F_COL = QColor(0x38, 0xbd, 0xf8)
POS_COL = QColor(0xfa, 0xcc, 0x15)
TEXT_COL = QColor(0xb6, 0xbe, 0xca)

MONO = "Consolas"


def _clamp1(v: float) -> float:
    return max(-1.0, min(1.0, v))


class YokeView(QWidget):
    """Front-on yoke/wheel drawing with commanded force arrows (port of DeviceView)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumSize(300, 240)
        self._roll = 0.0
        self._pitch = 0.0
        self._fx = 0.0
        self._fy = 0.0
        self._cmd_deg = float("nan")
        self._connected = False
        self.rotation_range_deg = 180.0

    def set_state(self, roll_norm, pitch_norm, force_x, force_y,
                  command_direction_deg, device_connected) -> None:
        self._roll = _clamp1(roll_norm)
        self._pitch = _clamp1(pitch_norm)
        self._fx = force_x
        self._fy = force_y
        self._cmd_deg = command_direction_deg
        self._connected = device_connected
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), BG)
        w, h = self.width(), self.height()
        cx = w * 0.5
        cy = h * 0.52
        unit = min(w, h) * 0.30
        self._draw_reference(p, cx, cy, unit)
        self._draw_yoke(p, cx, cy, unit)
        self._draw_forces(p, cx, cy, unit)
        self._draw_position_map(p, QRectF(w - 138, h - 156, 112, 112))
        self._draw_axis_labels(p, cx, cy, unit)
        if not self._connected:
            p.setPen(QColor(0xf8, 0x71, 0x71))
            p.drawText(14, h - 24, "device not connected - showing commanded force only")

    def _draw_reference(self, p, cx, cy, unit):
        dash = QPen(GRID, 1)
        dash.setStyle(Qt.PenStyle.DashLine)
        p.setPen(dash)
        p.drawLine(QPointF(cx - unit * 1.6, cy), QPointF(cx + unit * 1.6, cy))
        p.drawLine(QPointF(cx, cy - unit * 1.4), QPointF(cx, cy + unit * 1.4))
        p.setPen(QPen(GRID, 1))
        r = unit * 0.5
        while r <= unit * 1.5:
            p.drawEllipse(QPointF(cx, cy), r, r)
            r += unit * 0.5

    def _draw_yoke(self, p, cx, cy, unit):
        pitch_shift = self._pitch * unit * 0.42
        scale = 1.0 + self._pitch * 0.13
        t = QTransform()
        t.translate(cx, cy + pitch_shift)
        t.scale(scale, scale)
        t.rotate(self._roll * self.rotation_range_deg / 2.0)
        p.setTransform(t)
        rim = unit
        thick = max(3.0, unit * 0.055)
        pen = QPen(YOKE, thick)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawLine(QPointF(0, -rim * 0.25), QPointF(0, -rim * 1.5))
        p.drawArc(QRectF(-rim, -rim, rim * 2, rim * 2), 125 * 16, 290 * 16)
        p.drawLine(QPointF(-rim * 0.98, 0), QPointF(rim * 0.98, 0))
        gw = unit * 0.16
        gh = unit * 0.5
        p.setBrush(QBrush(YOKE))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(-rim * 0.98 - gw, -gh / 2, gw * 2, gh), gw * 0.6, gw * 0.6)
        p.drawRoundedRect(QRectF(rim * 0.98 - gw, -gh / 2, gw * 2, gh), gw * 0.6, gw * 0.6)
        hr = unit * 0.17
        p.setBrush(QBrush(HUB))
        p.drawEllipse(QPointF(0, 0), hr, hr)
        p.setPen(QPen(YOKE_DIM, thick * 0.5))
        p.drawEllipse(QPointF(0, 0), hr, hr)
        p.resetTransform()

    def _draw_forces(self, p, cx, cy, unit):
        hub_y = cy + self._pitch * unit * 0.42
        hub = QPointF(cx, hub_y)
        fx = self._fx / 10000.0
        fy = self._fy / 10000.0
        length = unit * 1.35
        font = QFont(MONO, 9)
        if abs(fx) > 0.01:
            pen = QPen(FX_COL, 4)
            to = QPointF(hub.x() + fx * length, hub.y())
            self._arrow(p, pen, FX_COL, hub, to)
        if abs(fy) > 0.01:
            pen = QPen(FY_COL, 4)
            to = QPointF(hub.x(), hub.y() + fy * length)
            self._arrow(p, pen, FY_COL, hub, to)
        mag = math.hypot(fx, fy)
        if mag > 0.01:
            pen = QPen(F_COL, 6)
            to = QPointF(hub.x() + fx * length, hub.y() + fy * length)
            self._arrow(p, pen, F_COL, hub, to)
        p.setFont(font)
        p.setPen(FX_COL)
        p.drawText(QPointF(cx + unit * 0.9, cy - unit * 1.32), f"Fx {self._fx:+7.0f}")
        p.setPen(FY_COL)
        p.drawText(QPointF(cx + unit * 0.9, cy - unit * 1.18), f"Fy {self._fy:+7.0f}")
        p.setPen(F_COL)
        p.drawText(QPointF(cx + unit * 0.9, cy - unit * 1.04), f"|F| {mag * 10000:6.0f}")
        if not math.isnan(self._cmd_deg):
            p.setPen(TEXT_COL)
            p.drawText(QPointF(cx + unit * 0.9, cy - unit * 0.90), f"cmd {self._cmd_deg:5.1f} deg")

    def _arrow(self, p, pen, color, frm, to):
        p.setPen(pen)
        p.drawLine(frm, to)
        a = math.atan2(to.y() - frm.y(), to.x() - frm.x())
        hs = 11.0
        p1 = QPointF(to.x() - hs * math.cos(a - 0.5), to.y() - hs * math.sin(a - 0.5))
        p2 = QPointF(to.x() - hs * math.cos(a + 0.5), to.y() - hs * math.sin(a + 0.5))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(color))
        p.drawPolygon([to, p1, p2])

    def _draw_position_map(self, p, box):
        p.setPen(QPen(GRID, 1))
        p.drawRect(box)
        p.drawLine(QPointF(box.x(), box.y() + box.height() / 2),
                   QPointF(box.right(), box.y() + box.height() / 2))
        p.drawLine(QPointF(box.x() + box.width() / 2, box.y()),
                   QPointF(box.x() + box.width() / 2, box.bottom()))
        px = box.x() + box.width() / 2 + self._roll * box.width() / 2 * 0.92
        py = box.y() + box.height() / 2 + self._pitch * box.height() / 2 * 0.92
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(POS_COL))
        p.drawEllipse(QPointF(px, py), 4, 4)
        p.setPen(TEXT_COL)
        p.setFont(QFont(MONO, 8))
        p.drawText(QPointF(box.x() + 1, box.y() - 4), "position")
        p.drawText(QPointF(box.x() + 1, box.bottom() + 12),
                   f"R {self._roll:+5.2f}   P {self._pitch:+5.2f}")

    def _draw_axis_labels(self, p, cx, cy, unit):
        f = QFont(MONO, 8, QFont.Weight.Bold)
        p.setFont(f)
        p.setPen(TEXT_COL)
        p.drawText(QPointF(cx - unit * 1.6, cy - 4), "ROLL -  (left)")
        p.drawText(QPointF(cx + unit * 1.6 - 110, cy - 4), "ROLL +  (right)")
        p.drawText(QPointF(cx - 90, cy - unit * 1.4), "PITCH -  (push / nose-down)")
        p.drawText(QPointF(cx - 82, cy + unit * 1.32), "PITCH +  (pull / nose-up)")


class SliderRow(QWidget):
    valueChanged = pyqtSignal(int)

    def __init__(self, label: str, minimum: int, maximum: int, value: int,
                 increment: int = 1, vertical: bool = False, parent=None) -> None:
        super().__init__(parent)
        self._label = QLabel(label)
        self._bar = QSlider(Qt.Orientation.Horizontal)
        self._bar.setRange(minimum, maximum)
        self._bar.setSingleStep(increment)
        self._bar.setPageStep(max(increment, (maximum - minimum) // 10))
        self._num = QSpinBox()
        self._num.setRange(minimum, maximum)
        self._num.setSingleStep(increment)
        self._num.setValue(value)
        self._bar.setValue(value)
        self._bar.valueChanged.connect(self._from_bar)
        self._num.valueChanged.connect(self._from_num)
        self._sync = False

        root = QGridLayout()
        root.setContentsMargins(0, 0, 0, 0)
        if vertical:
            root.addWidget(self._label, 0, 0)
            root.addWidget(self._bar, 1, 0)
            root.addWidget(self._num, 1, 1)
            root.setColumnStretch(0, 1)
        else:
            root.addWidget(self._label, 0, 0)
            root.addWidget(self._bar, 0, 1)
            root.addWidget(self._num, 0, 2)
            root.setColumnStretch(1, 1)
            root.setColumnMinimumWidth(0, 128)
        self.setLayout(root)
        self.setMinimumHeight(46 if vertical else 30)

    def _from_bar(self, v: int) -> None:
        if self._sync:
            return
        self._sync = True
        self._num.setValue(v)
        self._sync = False
        self.valueChanged.emit(v)

    def _from_num(self, v: int) -> None:
        if self._sync:
            return
        self._sync = True
        self._bar.setValue(v)
        self._sync = False
        self.valueChanged.emit(v)

    def value(self) -> int:
        return self._num.value()

    def set_value(self, v: int) -> None:
        v = max(self._num.minimum(), min(self._num.maximum(), int(v)))
        self._sync = True
        self._num.setValue(v)
        self._bar.setValue(v)
        self._sync = False

    def set_enabled(self, enabled: bool) -> None:
        self._bar.setEnabled(enabled)
        self._num.setEnabled(enabled)
        self._label.setStyleSheet("" if enabled else "color: gray;")

    def set_label_row_control(self, w: QWidget) -> None:
        grid = self.layout()
        if grid.columnCount() >= 3:
            grid.addWidget(w, 0, 2)
        else:
            grid.addWidget(w, 0, 1)


class DirPad(QWidget):
    change_requested = pyqtSignal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        self._readout = QLabel("270 deg")
        self._readout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(self._button("push 180", 180), 0, 1)
        grid.addWidget(self._button("left 90", 90), 1, 0)
        grid.addWidget(self._readout, 1, 1)
        grid.addWidget(self._button("right 270", 270), 1, 2)
        grid.addWidget(self._button("pull 0", 0), 2, 1)
        for c in range(3):
            grid.setColumnStretch(c, 1)
            grid.setRowStretch(c, 1)
        self.setLayout(grid)
        self.setMinimumHeight(84)

    def _button(self, text: str, deg: int) -> QPushButton:
        b = QPushButton(text)
        b.clicked.connect(lambda: self.change_requested.emit(deg))
        return b

    def set_readout(self, deg: int) -> None:
        self._readout.setText(f"{deg} deg")

    def set_enabled(self, enabled: bool) -> None:
        for b in self.findChildren(QPushButton):
            b.setEnabled(enabled)


class CollapsibleGroup(QGroupBox):
    def __init__(self, title: str, height: int, collapsible: bool = True,
                 parent=None) -> None:
        super().__init__(title, parent)
        self._title = title
        self._open_height = height
        self._collapsible = collapsible
        self._collapsed = False
        self.setMinimumHeight(height)
        self._update_caption()

    def _update_caption(self) -> None:
        if self._collapsible:
            self.setTitle((">  " if self._collapsed else "v  ") + self._title)
        else:
            self.setTitle(self._title)

    def mousePressEvent(self, event) -> None:
        if (self._collapsible
                and event.button() == Qt.MouseButton.LeftButton
                and event.position().y() <= 20):
            self.toggle_collapsed()
        else:
            super().mousePressEvent(event)

    def set_collapsed(self, collapsed: bool) -> None:
        if not self._collapsible or self._collapsed == collapsed:
            return
        self._collapsed = collapsed
        for w in self.findChildren(QWidget):
            w.setVisible(not collapsed)
        self.setMinimumHeight(22 if collapsed else self._open_height)
        self._update_caption()

    @property
    def collapsed(self) -> bool:
        return self._collapsed

    def toggle_collapsed(self) -> None:
        if self._collapsible:
            self.set_collapsed(not self._collapsed)

    def set_body_enabled(self, on: bool) -> None:
        for w in self.findChildren(QWidget):
            w.setEnabled(on)
        self.setStyleSheet("" if on else "QGroupBox { color: gray; }")


__all__ = ["YokeView", "SliderRow", "DirPad", "CollapsibleGroup"]
