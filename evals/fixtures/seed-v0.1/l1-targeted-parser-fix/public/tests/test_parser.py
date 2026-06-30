import unittest
from kvrecord import ParseError, parse_record


class ParserTests(unittest.TestCase):
    def test_basic_record(self):
        self.assertEqual(parse_record("a=1;b=2"), {"a": "1", "b": "2"})

    def test_empty_record(self):
        self.assertEqual(parse_record(""), {})

    def test_errors(self):
        for text in ["missing", "=value", "a=1;a=2"]:
            with self.subTest(text=text), self.assertRaises(ParseError):
                parse_record(text)


if __name__ == "__main__":
    unittest.main()
