import copy
import unittest

from crm.features.contact_list_pagination import run_feature


def _contact(pk, name, email="", phone="", company=""):
    return {"pk": pk, "name": name, "email": email, "phone": phone, "company": company}


class ContactListPaginationCommunityTests(unittest.TestCase):
    def test_search_case_insensitive_and_strip(self):
        contacts = [
            _contact(2, "Marina Silva", "marina@example.com", "", "Padaria"),
            _contact(1, "Ana Souza"),
        ]
        out = run_feature({"contacts": contacts, "q": "  MARINA  "})
        self.assertEqual(out["q"], "MARINA")
        self.assertEqual(out["total_count"], 1)
        self.assertEqual(len(out["results"]), 1)
        self.assertEqual(out["results"][0]["pk"], 2)

    def test_search_across_email_phone_company(self):
        contacts = [
            _contact(1, "Ana", "ana@test.com"),
            _contact(2, "Beto", "", "555-1234"),
            _contact(3, "Cris", "", "", "Padaria Luz"),
        ]
        self.assertEqual(run_feature({"contacts": contacts, "q": "ANA@TEST"})["total_count"], 1)
        self.assertEqual(run_feature({"contacts": contacts, "q": "555"})["total_count"], 1)
        self.assertEqual(run_feature({"contacts": contacts, "q": "padaria"})["total_count"], 1)
        self.assertEqual(run_feature({"contacts": contacts, "q": ""})["total_count"], 3)
        self.assertEqual(run_feature({"contacts": contacts})["total_count"], 3)

    def test_sort_by_name_then_pk(self):
        contacts = [
            _contact(2, "Marina Silva", "marina@example.com", "", "Padaria"),
            _contact(1, "Ana Souza"),
            _contact(5, "Ana Souza"),
        ]
        out = run_feature({"contacts": contacts, "q": ""})
        self.assertEqual([r["pk"] for r in out["results"]], [1, 5, 2])

    def test_empty_result_is_page_one_of_one(self):
        out = run_feature({"contacts": [], "q": "zzz", "page": 1})
        self.assertEqual(out["total_count"], 0)
        self.assertEqual(out["total_pages"], 1)
        self.assertEqual(out["page_effective"], 1)
        self.assertEqual(out["per_page"], 50)
        self.assertEqual(out["results"], [])
        self.assertFalse(out["has_previous"])
        self.assertFalse(out["has_next"])
        self.assertIsNone(out["prev_page"])
        self.assertIsNone(out["next_page"])

    def test_page_fallback_to_one(self):
        contacts = [_contact(1, "Ana"), _contact(2, "Beto")]
        for page in [None, "", "   ", "abc", "12x", "++1"]:
            with self.subTest(page=page):
                out = run_feature({"contacts": contacts, "q": "", "page": page})
                self.assertEqual(out["page_effective"], 1)
        out = run_feature({"contacts": contacts, "q": ""})
        self.assertEqual(out["page_effective"], 1)

    def test_page_zero_negative_beyond_last_yields_last(self):
        contacts = []
        i = 0
        while i < 55:
            contacts.append(_contact(i + 1, "N%03d" % (i + 1)))
            i = i + 1
        out = run_feature({"contacts": contacts, "q": "", "page": 2})
        self.assertEqual(out["total_count"], 55)
        self.assertEqual(out["total_pages"], 2)
        self.assertEqual(out["page_effective"], 2)
        self.assertEqual(len(out["results"]), 5)
        self.assertTrue(out["has_previous"])
        self.assertFalse(out["has_next"])
        self.assertEqual(out["prev_page"], 1)
        self.assertIsNone(out["next_page"])
        for page in [0, -1, -50, 99, "99", 3]:
            with self.subTest(page=page):
                o2 = run_feature({"contacts": contacts, "q": "", "page": page})
                self.assertEqual(o2["page_effective"], 2)
                self.assertEqual(len(o2["results"]), 5)

    def test_valid_page_slice_and_nav_flags(self):
        contacts = []
        i = 0
        while i < 120:
            contacts.append(_contact(i + 1, "A%03d" % (i + 1)))
            i = i + 1
        out = run_feature({"contacts": contacts, "q": "", "page": 2})
        self.assertEqual(out["page_effective"], 2)
        self.assertEqual(out["total_pages"], 3)
        self.assertEqual(len(out["results"]), 50)
        self.assertTrue(out["has_previous"])
        self.assertTrue(out["has_next"])
        self.assertEqual(out["prev_page"], 1)
        self.assertEqual(out["next_page"], 3)
        self.assertEqual(out["results"][0]["name"], "A051")
        out_s = run_feature({"contacts": contacts, "q": "", "page": " 2 "})
        self.assertEqual(out_s["page_effective"], 2)

    def test_malformed_raises(self):
        good = _contact(1, "Ana")
        bad_payloads = [
            "x",
            [],
            None,
            {"contacts": "x"},
            {"contacts": [good], "q": 123},
            {"contacts": [good], "page": 1.5},
            {"contacts": [good], "page": True},
            {"contacts": [good], "page": False},
            {"contacts": [{"name": "Ana", "email": "", "phone": "", "company": ""}]},
            {"contacts": [{"pk": True, "name": "Ana", "email": "", "phone": "", "company": ""}]},
            {"contacts": [{"pk": 0, "name": "Ana", "email": "", "phone": "", "company": ""}]},
            {"contacts": [{"pk": 1, "name": "", "email": "", "phone": "", "company": ""}]},
            {"contacts": "notalist"},
        ]
        for p in bad_payloads:
            with self.subTest(p=p):
                with self.assertRaises(ValueError):
                    run_feature(p)
        many = []
        i = 0
        while i < 2001:
            many.append(_contact(i + 1, "Z"))
            i = i + 1
        with self.assertRaises(ValueError):
            run_feature({"contacts": many})

    def test_no_mutation_extra_keys_and_copy(self):
        contacts = [
            {"pk": 2, "name": "Marina Silva", "email": "m@e.com", "phone": "", "company": "P", "owner_id": 9},
            {"pk": 1, "name": "Ana Souza", "email": "", "phone": "", "company": "", "x": 1},
        ]
        payload = {"contacts": contacts, "q": "marina", "page": 1, "extra": 123}
        before = copy.deepcopy(payload)
        out = run_feature(payload)
        self.assertEqual(payload, before)
        self.assertEqual(set(out["results"][0].keys()), {"pk", "name", "email", "phone", "company"})
        out["results"][0]["name"] = "MUT"
        self.assertEqual(contacts[0]["name"], "Marina Silva")

    def test_q_truncation_to_200(self):
        contacts = [_contact(1, "Ana")]
        long_q = "  " + "x" * 500 + "  "
        out = run_feature({"contacts": contacts, "q": long_q})
        self.assertEqual(out["q"], "x" * 200)


if __name__ == "__main__":
    unittest.main()
