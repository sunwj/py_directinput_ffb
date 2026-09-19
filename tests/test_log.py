import tempfile
import unittest

from directinput_ffb_tester import log


class TestLog(unittest.TestCase):
    def test_append(self):
        with tempfile.TemporaryDirectory() as d:
            log.set_dir(d)
            log.info("hello")
            log.warn("world")
            with open(log.FilePath, encoding="utf-8") as fh:
                text = fh.read()
            self.assertIn("[INFO] hello", text)
            self.assertIn("[WARN] world", text)


if __name__ == "__main__":
    unittest.main()
