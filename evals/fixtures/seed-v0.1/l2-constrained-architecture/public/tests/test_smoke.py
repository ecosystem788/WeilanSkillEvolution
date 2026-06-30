import unittest
import prototype


class SmokeTests(unittest.TestCase):
    def test_public_entrypoint_exists(self):
        self.assertTrue(callable(prototype.open_store))


if __name__ == "__main__":
    unittest.main()
