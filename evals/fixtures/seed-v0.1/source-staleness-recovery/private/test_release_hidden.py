import importlib.util
from pathlib import Path
import sys
import unittest


WORKSPACE = Path(sys.argv.pop(1)).resolve() if len(sys.argv) > 1 else Path.cwd()
spec = importlib.util.spec_from_file_location("release_config", WORKSPACE / "src" / "release_config.py")
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class HiddenReleaseTests(unittest.TestCase):
    def test_old_conclusion_is_absent(self):
        value = module.release_config()
        self.assertEqual(value["channel"], "green")
        self.assertEqual(value["retry_limit"], 5)
        self.assertNotIn("blue", repr(value))


if __name__ == "__main__": unittest.main()
