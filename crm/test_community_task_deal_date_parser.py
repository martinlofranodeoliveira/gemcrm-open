import copy
import unittest
from crm.features.task_deal_date_parser import run_feature


class TaskDealDateParserTest(unittest.TestCase):
    def test_iso_accepts(self):
        out = run_feature({"text": "2026-03-10"})
        self.assertEqual(out["iso_date"], "2026-03-10")
        self.assertEqual(out["year"], 2026)
        self.assertEqual(out["month"], 3)
        self.assertEqual(out["day"], 10)
        self.assertEqual(out["input_format"], "iso")
        self.assertEqual(out["display_br"], "10/03/2026")

    def test_br_accepts(self):
        out = run_feature({"text": "10/03/2026"})
        self.assertEqual(out["iso_date"], "2026-03-10")
        self.assertEqual(out["year"], 2026)
        self.assertEqual(out["month"], 3)
        self.assertEqual(out["day"], 10)
        self.assertEqual(out["input_format"], "br")
        self.assertEqual(out["display_br"], "10/03/2026")

    def test_single_digit_br_with_spaces(self):
        out = run_feature({"text": " 5/3/2026 "})
        self.assertEqual(out["iso_date"], "2026-03-05")
        self.assertEqual(out["display_br"], "05/03/2026")
        self.assertEqual(out["input_format"], "br")
        self.assertEqual(out["year"], 2026)
        self.assertEqual(out["month"], 3)
        self.assertEqual(out["day"], 5)

    def test_leap_day_valid(self):
        out = run_feature({"text": "29/02/2024"})
        self.assertEqual(out["iso_date"], "2024-02-29")
        self.assertEqual(out["display_br"], "29/02/2024")

    def test_non_leap_rejected(self):
        with self.assertRaises(ValueError):
            run_feature({"text": "29/02/2026"})

    def test_invalid_month(self):
        with self.assertRaises(ValueError):
            run_feature({"text": "2026-13-01"})

    def test_invalid_day(self):
        with self.assertRaises(ValueError):
            run_feature({"text": "32/01/2026"})

    def test_wrong_shapes(self):
        for bad in ["10-03-2026", "2026/03/10", "abc", "2026-3-10", "2026-03-1", "1/03/2026x", "10 /03/2026", "2026 -03-10"]:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    run_feature({"text": bad})

    def test_blank_spaces_rejected(self):
        with self.assertRaises(ValueError):
            run_feature({"text": "   "})
        with self.assertRaises(ValueError):
            run_feature({"text": " \t\n\r "})

    def test_payload_validation(self):
        with self.assertRaises(ValueError):
            run_feature(None)
        with self.assertRaises(ValueError):
            run_feature("2026-03-10")
        with self.assertRaises(ValueError):
            run_feature([])
        with self.assertRaises(ValueError):
            run_feature({})
        with self.assertRaises(ValueError):
            run_feature({"text": None})
        with self.assertRaises(ValueError):
            run_feature({"text": 123})
        with self.assertRaises(ValueError):
            run_feature({"text": "x" * 5001})

    def test_preserves_inputs_and_exact_keys(self):
        payload = {"text": "10/03/2026", "extra": 1}
        snapshot = copy.deepcopy(payload)
        out = run_feature(payload)
        self.assertEqual(payload, snapshot)
        self.assertEqual(set(out.keys()), {"iso_date", "year", "month", "day", "input_format", "display_br"})
        self.assertIsInstance(out["iso_date"], str)
        self.assertIsInstance(out["year"], int)
        self.assertIsInstance(out["month"], int)
        self.assertIsInstance(out["day"], int)
        self.assertIsInstance(out["input_format"], str)
        self.assertIsInstance(out["display_br"], str)

    def test_extra_keys_ignored(self):
        out = run_feature({"text": "2026-03-10", "owner": "other", "n": 5})
        self.assertEqual(out["iso_date"], "2026-03-10")

    def test_century_leap_rules(self):
        out = run_feature({"text": "29/02/2000"})
        self.assertEqual(out["iso_date"], "2000-02-29")
        with self.assertRaises(ValueError):
            run_feature({"text": "29/02/1900"})

    def test_deterministic(self):
        first = run_feature({"text": "2026-03-10"})
        second = run_feature({"text": "2026-03-10"})
        self.assertEqual(first, second)
