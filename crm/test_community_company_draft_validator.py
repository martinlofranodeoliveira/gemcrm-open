import unittest

from crm.features.company_draft_validator import run_feature


class CompanyDraftValidatorTest(unittest.TestCase):
    def test_valid_trimmed(self):
        payload = {"name": " Padaria Pao Novo ", "website": "https://exemplo.com", "notes": "Fictional example"}
        snapshot = dict(payload)
        result = run_feature(payload)
        self.assertEqual(payload, snapshot)
        self.assertTrue(result["valid"])
        self.assertEqual(result["errors"], {})
        self.assertEqual(result["normalized"], {"name": "Padaria Pao Novo", "website": "https://exemplo.com", "notes": "Fictional example"})

    def test_missing_name(self):
        payload = {"website": "https://exemplo.com", "notes": "x"}
        snapshot = dict(payload)
        result = run_feature(payload)
        self.assertEqual(payload, snapshot)
        self.assertFalse(result["valid"])
        self.assertEqual(result["errors"], {"name": "name is required"})
        self.assertIsNone(result["normalized"])

    def test_null_blank_and_non_string_name(self):
        for bad in [None, "   \t\n\r  ", 123, ["x"]]:
            payload = {"name": bad}
            snapshot = dict(payload)
            result = run_feature(payload)
            self.assertEqual(payload, snapshot)
            self.assertFalse(result["valid"])
            self.assertIn("name", result["errors"])
            self.assertIsNone(result["normalized"])
        self.assertEqual(run_feature({"name": None})["errors"]["name"], "name is required")
        self.assertEqual(run_feature({"name": "   "})["errors"]["name"], "name is required")
        self.assertEqual(run_feature({"name": 123})["errors"]["name"], "name must be a string")

    def test_overlong_name(self):
        payload = {"name": "n" * 181}
        result = run_feature(payload)
        self.assertFalse(result["valid"])
        self.assertEqual(result["errors"], {"name": "name must be at most 180 characters"})
        self.assertIsNone(result["normalized"])

    def test_website_cases(self):
        self.assertEqual(run_feature({"name": "Acme", "website": "exemplo"})["errors"], {"website": "website must be a valid URL or empty"})
        self.assertEqual(run_feature({"name": "Acme", "website": 123})["errors"], {"website": "website must be a valid URL or empty"})
        long_site = "https://" + "a" * 190 + ".com"
        bad_long = run_feature({"name": "Acme", "website": long_site})
        self.assertFalse(bad_long["valid"])
        self.assertIn("website", bad_long["errors"])
        ok_empty = run_feature({"name": "Acme", "website": "   "})
        self.assertTrue(ok_empty["valid"])
        self.assertEqual(ok_empty["normalized"]["website"], "")
        ok_trim = run_feature({"name": "Acme", "website": "  https://exemplo.com  "})
        self.assertTrue(ok_trim["valid"])
        self.assertEqual(ok_trim["normalized"]["website"], "https://exemplo.com")

    def test_notes_cases(self):
        self.assertEqual(run_feature({"name": "Acme", "notes": 123})["errors"], {"notes": "notes must be a string"})
        bad_long = run_feature({"name": "Acme", "notes": "x" * 10001})
        self.assertFalse(bad_long["valid"])
        self.assertEqual(bad_long["errors"], {"notes": "notes must be at most 10000 characters"})
        self.assertIsNone(bad_long["normalized"])

    def test_combined_example(self):
        result = run_feature({"name": "   ", "website": "exemplo", "notes": 123})
        self.assertFalse(result["valid"])
        self.assertEqual(result["errors"], {"name": "name is required", "website": "website must be a valid URL or empty", "notes": "notes must be a string"})
        self.assertIsNone(result["normalized"])

    def test_extra_keys_defaults_and_non_object(self):
        result = run_feature({"name": "Acme", "extra": 1})
        self.assertTrue(result["valid"])
        self.assertEqual(result["normalized"], {"name": "Acme", "website": "", "notes": ""})
        only_name = run_feature({"name": "Acme"})
        self.assertEqual(only_name["normalized"]["website"], "")
        self.assertEqual(only_name["normalized"]["notes"], "")
        for bad in [None, [], "x", 123, True]:
            with self.assertRaises(ValueError):
                run_feature(bad)

    def test_pure_deterministic(self):
        payload = {"name": " Acme ", "website": "http://exemplo.com", "notes": "keep  "}
        first = run_feature(payload)
        second = run_feature({"name": " Acme ", "website": "http://exemplo.com", "notes": "keep  "})
        self.assertEqual(first, second)
        self.assertEqual(first["normalized"]["name"], "Acme")
        self.assertEqual(first["normalized"]["notes"], "keep  ")
