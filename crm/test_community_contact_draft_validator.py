import copy
import unittest

from crm.features.contact_draft_validator import run_feature


class ContactDraftValidatorCommunityTest(unittest.TestCase):
    def test_valid_with_surrounding_whitespace(self):
        payload = {
            "name": "  Marina Silva \t\n",
            "email": "  marina@example.com  ",
            "phone": "  +55 11 99999-0000  ",
            "company": "  Padaria Estrela  ",
            "notes": "\tFictional example\n",
        }
        result = run_feature(payload)
        self.assertTrue(result["valid"])
        self.assertEqual(result["errors"], {})
        self.assertEqual(result["normalized"], {
            "name": "Marina Silva",
            "email": "marina@example.com",
            "phone": "+55 11 99999-0000",
            "company": "Padaria Estrela",
            "notes": "Fictional example",
        })

    def test_blank_name_requires_name(self):
        result = run_feature({
            "name": "   \t\n  ",
            "email": "",
            "phone": "",
            "company": "",
            "notes": "",
        })
        self.assertFalse(result["valid"])
        self.assertEqual(result["errors"], {"name": "required"})
        self.assertEqual(result["normalized"]["name"], "")

    def test_empty_payload_requires_name(self):
        result = run_feature({})
        self.assertFalse(result["valid"])
        self.assertEqual(result["errors"], {"name": "required"})
        self.assertEqual(result["normalized"], {
            "name": "",
            "email": "",
            "phone": "",
            "company": "",
            "notes": "",
        })

    def test_bad_email_and_phone_without_digits(self):
        result = run_feature({
            "name": "Ana",
            "email": "bad-email",
            "phone": "abc",
            "company": "",
            "notes": "",
        })
        self.assertFalse(result["valid"])
        self.assertEqual(result["errors"], {"email": "invalid", "phone": "invalid"})
        self.assertEqual(result["normalized"]["email"], "bad-email")
        self.assertEqual(result["normalized"]["phone"], "abc")

    def test_phone_without_any_digit_is_invalid(self):
        result = run_feature({"name": "Ana", "phone": "+++--- ((.))"})
        self.assertFalse(result["valid"])
        self.assertEqual(result["errors"]["phone"], "invalid")

    def test_email_edge_shapes_are_invalid(self):
        bad_values = [
            "a@b",
            "a@.b.com",
            "a@b.com.",
            "a@b..com",
            "a@b.c",
            "a b@c.com",
            "a@@b.com",
            "@b.com",
            "a@",
        ]
        for bad in bad_values:
            with self.subTest(bad=bad):
                result = run_feature({"name": "Ana", "email": bad})
                self.assertFalse(result["valid"])
                self.assertEqual(result["errors"]["email"], "invalid")

    def test_raw_over_10000_raises(self):
        with self.assertRaises(ValueError):
            run_feature({"name": "x" * 10001})
        with self.assertRaises(ValueError):
            run_feature({"notes": "y" * 10001})

    def test_non_string_field_raises(self):
        with self.assertRaises(ValueError):
            run_feature({"name": 123})
        with self.assertRaises(ValueError):
            run_feature({"email": ["a@b.com"]})
        with self.assertRaises(ValueError):
            run_feature({"phone": {}})
        with self.assertRaises(ValueError):
            run_feature(["not", "a", "dict"])
        with self.assertRaises(ValueError):
            run_feature(None)

    def test_extra_keys_ignored_and_input_not_mutated(self):
        payload = {
            "name": "Joao",
            "email": "",
            "phone": "",
            "company": "",
            "notes": "ok",
            "extra": "ignore me",
            "other": 123,
        }
        snapshot = copy.deepcopy(payload)
        result = run_feature(payload)
        self.assertEqual(payload, snapshot)
        self.assertTrue(result["valid"])
        self.assertEqual(result["errors"], {})
        self.assertEqual(set(result["normalized"].keys()), {"name", "email", "phone", "company", "notes"})
        self.assertNotIn("extra", result["errors"])
        self.assertNotIn("extra", result["normalized"])

    def test_overlong_notes_reports_too_long(self):
        payload = {"name": "Lia", "notes": "n" * 2001}
        snapshot = copy.deepcopy(payload)
        result = run_feature(payload)
        self.assertEqual(payload, snapshot)
        self.assertFalse(result["valid"])
        self.assertEqual(result["errors"], {"notes": "too_long"})
        self.assertEqual(len(result["normalized"]["notes"]), 2001)

    def test_none_defaults_to_empty(self):
        result = run_feature({"name": "Rui", "email": None, "phone": None, "company": None, "notes": None})
        self.assertTrue(result["valid"])
        self.assertEqual(result["normalized"], {
            "name": "Rui",
            "email": "",
            "phone": "",
            "company": "",
            "notes": "",
        })

    def test_length_boundaries(self):
        long_name = run_feature({"name": "n" * 181})
        self.assertEqual(long_name["errors"], {"name": "too_long"})
        long_email = run_feature({"name": "Ana", "email": "a" * 250 + "@b.co"})
        self.assertEqual(long_email["errors"]["email"], "too_long")
        long_phone = run_feature({"name": "Ana", "phone": "1" * 41})
        self.assertEqual(long_phone["errors"]["phone"], "too_long")
        long_company = run_feature({"name": "Ana", "company": "c" * 181})
        self.assertEqual(long_company["errors"]["company"], "too_long")


if __name__ == "__main__":
    unittest.main()
