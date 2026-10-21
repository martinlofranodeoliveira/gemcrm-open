import copy
import unittest

from crm.features.deal_draft_validator import run_feature


class DealDraftValidatorCommunityTests(unittest.TestCase):
    def test_minimal_valid_payload(self):
        result = run_feature({"title": "Mercado"})
        self.assertTrue(result["valid"])
        self.assertEqual(result["errors"], {})
        norm = result["normalized"]
        self.assertEqual(norm["title"], "Mercado")
        self.assertEqual(norm["value"], "0.00")
        self.assertEqual(norm["value_cents"], 0)
        self.assertEqual(norm["stage"], "new")
        self.assertIsNone(norm["expected_close"])
        self.assertIsNone(norm["company_pk"])
        self.assertIsNone(norm["contact_pk"])

    def test_trimmed_title_and_value_normalization(self):
        payload = {"title": " Padaria ", "value": "100.5", "stage": "new", "expected_close": None, "company_pk": None, "contact_pk": None}
        result = run_feature(payload)
        self.assertTrue(result["valid"])
        self.assertEqual(result["errors"], {})
        norm = result["normalized"]
        self.assertEqual(norm["title"], "Padaria")
        self.assertEqual(norm["value"], "100.50")
        self.assertEqual(norm["value_cents"], 10050)
        self.assertEqual(norm["stage"], "new")
        self.assertIsNone(norm["expected_close"])
        self.assertIsNone(norm["company_pk"])
        self.assertIsNone(norm["contact_pk"])

    def test_all_fields_invalid(self):
        payload = {"title": "", "value": "abc", "stage": "closed", "expected_close": "2026-02-30", "company_pk": 0, "contact_pk": False}
        result = run_feature(payload)
        self.assertFalse(result["valid"])
        self.assertIsNone(result["normalized"])
        self.assertEqual(result["errors"]["title"], "title is required")
        self.assertEqual(result["errors"]["value"], "value must be a decimal string")
        self.assertEqual(result["errors"]["stage"], "stage must be one of new, qualified, proposal, won, lost")
        self.assertEqual(result["errors"]["expected_close"], "expected_close must be YYYY-MM-DD valid calendar date")
        self.assertEqual(result["errors"]["company_pk"], "company_pk must be an integer 1 to 9007199254740991 or null")
        self.assertEqual(result["errors"]["contact_pk"], "contact_pk must be an integer 1 to 9007199254740991 or null")

    def test_non_object_raises_and_extra_keys_ignored_without_mutation(self):
        for bad in [None, [], "x", 123, 1.5, True]:
            with self.assertRaises(ValueError):
                run_feature(bad)
        payload = {"title": "Mercado", "extra": "ignore-me", "other": 123}
        snapshot = copy.deepcopy(payload)
        result = run_feature(payload)
        self.assertTrue(result["valid"])
        self.assertEqual(payload, snapshot)
        self.assertNotIn("extra", result["normalized"])
        self.assertNotIn("other", result["normalized"])
        self.assertEqual(result["normalized"]["title"], "Mercado")

    def test_leap_day_forecast(self):
        ok = run_feature({"title": "A", "expected_close": "2024-02-29"})
        self.assertTrue(ok["valid"])
        self.assertEqual(ok["normalized"]["expected_close"], "2024-02-29")
        bad1 = run_feature({"title": "A", "expected_close": "2026-02-29"})
        self.assertFalse(bad1["valid"])
        self.assertEqual(bad1["errors"]["expected_close"], "expected_close must be YYYY-MM-DD valid calendar date")
        self.assertIsNone(bad1["normalized"])
        bad2 = run_feature({"title": "A", "expected_close": "2026-13-01"})
        self.assertFalse(bad2["valid"])
        self.assertEqual(bad2["errors"]["expected_close"], "expected_close must be YYYY-MM-DD valid calendar date")

    def test_bool_zero_links_and_large_value(self):
        r1 = run_feature({"title": "A", "company_pk": False, "contact_pk": 0})
        self.assertFalse(r1["valid"])
        self.assertEqual(r1["errors"]["company_pk"], "company_pk must be an integer 1 to 9007199254740991 or null")
        self.assertEqual(r1["errors"]["contact_pk"], "contact_pk must be an integer 1 to 9007199254740991 or null")
        r2 = run_feature({"title": "A", "company_pk": True})
        self.assertFalse(r2["valid"])
        self.assertIn("company_pk", r2["errors"])
        r3 = run_feature({"title": "A", "value": "1000000000000.00"})
        self.assertFalse(r3["valid"])
        self.assertEqual(r3["errors"]["value"], "value is too large")
        self.assertIsNone(r3["normalized"])

    def test_canonical_two_decimals_without_separator(self):
        cases = [
            ("100", "100.00", 10000),
            ("100.5", "100.50", 10050),
            ("100.05", "100.05", 10005),
            ("0", "0.00", 0),
            ("0.5", "0.50", 50),
            ("1000", "1000.00", 100000),
        ]
        for raw, canon, cents in cases:
            with self.subTest(raw=raw):
                result = run_feature({"title": "T", "value": raw})
                self.assertTrue(result["valid"])
                self.assertEqual(result["normalized"]["value"], canon)
                self.assertEqual(result["normalized"]["value_cents"], cents)
                self.assertNotIn(",", result["normalized"]["value"])
                parts = result["normalized"]["value"].split(".")
                self.assertEqual(len(parts), 2)
                self.assertEqual(len(parts[1]), 2)
