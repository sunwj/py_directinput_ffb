import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import unittest

from PyQt6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])


class TestWindow(unittest.TestCase):
    def test_construct_smoke(self):
        from directinput_ffb_tester.window import MainWindow
        w = MainWindow()
        self.assertIn("FFB device", w._status.text())
        self.assertTrue(w._grp_periodic.collapsed)
        self.assertTrue(w._grp_ramp.collapsed)
        self.assertTrue(w._grp_condition.collapsed)
        self.assertFalse(w._grp_envelope.collapsed)
        w.close()

    def test_spring_controls_populate_effect_spec(self):
        from directinput_ffb_tester.window import MainWindow

        w = MainWindow()
        w._spring_mag.set_value(6100)
        w._spring_neg_coef.set_value(4200)
        w._spring_pos_sat.set_value(9000)
        w._spring_neg_sat.set_value(7000)
        w._spring_dead_band.set_value(1200)
        w._spring_offx.set_value(300)
        w._spring_offy.set_value(-400)
        spec = w._spring_spec()
        self.assertEqual(spec.positive_coefficient, 6100)
        self.assertEqual(spec.negative_coefficient, 4200)
        self.assertEqual(spec.positive_saturation, 9000)
        self.assertEqual(spec.negative_saturation, 7000)
        self.assertEqual(spec.dead_band, 1200)
        self.assertEqual(spec.center_offset_x, 300)
        self.assertEqual(spec.center_offset_y, -400)
        w.close()


if __name__ == "__main__":
    unittest.main()
