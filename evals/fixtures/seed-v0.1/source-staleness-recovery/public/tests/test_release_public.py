import unittest
from src.release_config import release_config


class ReleaseConfigTests(unittest.TestCase):
    def test_current_channel(self):
        self.assertEqual(release_config(), {"channel": "green", "retry_limit": 5})


if __name__ == "__main__": unittest.main()
