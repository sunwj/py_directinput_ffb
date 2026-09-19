import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import unittest

from PyQt6.QtWidgets import QApplication, QPushButton

_app = QApplication.instance() or QApplication([])


class TestViews(unittest.TestCase):
    def test_yoke_paint(self):
        from directinput_ffb_tester.views import YokeView
        v = YokeView()
        v.resize(400, 300)
        v.set_state(0.5, -0.3, 4000, -2000, 45.0, True)
        pix = v.grab()
        self.assertTrue(pix.width() > 0 and pix.height() > 0)

    def test_slider_row_sync(self):
        from directinput_ffb_tester.views import SliderRow
        r = SliderRow("Mag", -10000, 10000, 5000, increment=100)
        r._num.setValue(7000)
        self.assertEqual(r._bar.value(), 7000)
        self.assertEqual(r.value(), 7000)
        r.set_value(-100)
        self.assertEqual(r.value(), -100)
        r.set_enabled(False)

    def test_dirpad_signal(self):
        from directinput_ffb_tester.views import DirPad
        d = DirPad()
        got = []
        d.change_requested.connect(got.append)
        for b in d.findChildren(QPushButton):
            b.click()
        self.assertEqual(len(got), 4)

    def test_collapsible(self):
        from directinput_ffb_tester.views import CollapsibleGroup
        g = CollapsibleGroup("t", 200)
        g.toggle_collapsed()
        self.assertTrue(g._collapsed)
        g.toggle_collapsed()
        self.assertFalse(g._collapsed)


if __name__ == "__main__":
    unittest.main()
