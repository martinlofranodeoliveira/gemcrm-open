import copy
import unittest

from crm.features.deal_company_contact_link_check import run_feature


class DealCompanyContactLinkCheckTests(unittest.TestCase):
    def test_empty_payload(self):
        result = run_feature({})
        self.assertEqual(result, {
            "deal_count": 0,
            "linked_count": 0,
            "mismatched_count": 0,
            "dangling_company_count": 0,
            "dangling_contact_count": 0,
            "deals": [],
        })

    def test_matched_link(self):
        payload = {
            "companies": [{"pk": 1, "name": "Acme"}],
            "contacts": [{"pk": 10, "name": "Marina", "company_pk": 1}],
            "deals": [{"pk": 100, "title": "Site", "stage": "new", "company_pk": 1, "contact_pk": 10}],
        }
        result = run_feature(payload)
        self.assertEqual(result["deal_count"], 1)
        self.assertEqual(result["linked_count"], 1)
        self.assertEqual(result["mismatched_count"], 0)
        self.assertEqual(result["dangling_company_count"], 0)
        self.assertEqual(result["dangling_contact_count"], 0)
        entry = result["deals"][0]
        self.assertTrue(entry["company_exists"])
        self.assertTrue(entry["contact_exists"])
        self.assertTrue(entry["company_match"])
        self.assertEqual(entry["pk"], 100)

    def test_mismatched_link(self):
        payload = {
            "companies": [{"pk": 1, "name": "Acme"}, {"pk": 2, "name": "Beta"}],
            "contacts": [{"pk": 10, "name": "Ana", "company_pk": 2}],
            "deals": [
                {"pk": 100, "title": "Site", "stage": "qualified", "company_pk": 1, "contact_pk": 10},
                {"pk": 101, "title": "Solo", "stage": "new", "company_pk": None, "contact_pk": None},
            ],
        }
        result = run_feature(payload)
        self.assertEqual(result["deal_count"], 2)
        self.assertEqual(result["linked_count"], 1)
        self.assertEqual(result["mismatched_count"], 1)
        self.assertEqual(result["dangling_company_count"], 0)
        self.assertEqual(result["dangling_contact_count"], 0)
        self.assertFalse(result["deals"][0]["company_match"])
        self.assertTrue(result["deals"][0]["company_exists"])
        self.assertTrue(result["deals"][0]["contact_exists"])
        self.assertTrue(result["deals"][1]["company_match"])

    def test_dangling_links(self):
        payload = {
            "companies": [],
            "contacts": [],
            "deals": [{"pk": 5, "title": "Orfa", "stage": "proposal", "company_pk": 9, "contact_pk": 8}],
        }
        result = run_feature(payload)
        self.assertEqual(result["deal_count"], 1)
        self.assertEqual(result["linked_count"], 0)
        self.assertEqual(result["mismatched_count"], 0)
        self.assertEqual(result["dangling_company_count"], 1)
        self.assertEqual(result["dangling_contact_count"], 1)
        entry = result["deals"][0]
        self.assertFalse(entry["company_exists"])
        self.assertFalse(entry["contact_exists"])
        self.assertFalse(entry["company_match"])

    def test_unlinked_nulls(self):
        payload = {
            "companies": [],
            "contacts": [],
            "deals": [{"pk": 7, "title": "Free", "stage": "won", "company_pk": None, "contact_pk": None}],
        }
        result = run_feature(payload)
        self.assertEqual(result["deal_count"], 1)
        self.assertEqual(result["linked_count"], 0)
        self.assertEqual(result["mismatched_count"], 0)
        self.assertEqual(result["dangling_company_count"], 0)
        self.assertEqual(result["dangling_contact_count"], 0)
        entry = result["deals"][0]
        self.assertTrue(entry["company_exists"])
        self.assertTrue(entry["contact_exists"])
        self.assertTrue(entry["company_match"])

    def test_extra_keys_ignored_and_order_preserved(self):
        payload = {
            "companies": [{"pk": 1, "name": "Acme", "extra": "x"}],
            "contacts": [{"pk": 10, "name": "Marina", "company_pk": 1, "extra": 1}],
            "deals": [
                {"pk": 2, "title": "B", "stage": "new", "company_pk": 1, "contact_pk": 10, "extra": True},
                {"pk": 1, "title": "A", "stage": "lost", "company_pk": None, "contact_pk": None},
            ],
            "extra_root": 123,
        }
        result = run_feature(payload)
        self.assertEqual([d["pk"] for d in result["deals"]], [2, 1])
        self.assertEqual(result["deal_count"], 2)

    def test_malformed_payloads_raise(self):
        with self.assertRaises(ValueError):
            run_feature(None)
        with self.assertRaises(ValueError):
            run_feature([])
        with self.assertRaises(ValueError):
            run_feature({"companies": None, "contacts": [], "deals": []})
        with self.assertRaises(ValueError):
            run_feature({"companies": {}, "contacts": [], "deals": []})
        with self.assertRaises(ValueError):
            run_feature({"companies": [{"pk": 1, "name": "A"}] * 51, "contacts": [], "deals": []})
        with self.assertRaises(ValueError):
            run_feature({"companies": [{"pk": True, "name": "A"}], "contacts": [], "deals": []})
        with self.assertRaises(ValueError):
            run_feature({"companies": [{"pk": 1, "name": ""}], "contacts": [], "deals": []})
        with self.assertRaises(ValueError):
            run_feature({"companies": [{"pk": 1, "name": "A"}, {"pk": 1, "name": "B"}], "contacts": [], "deals": []})
        with self.assertRaises(ValueError):
            run_feature({"companies": [], "contacts": [{"pk": 1, "name": "A"}], "deals": []})
        with self.assertRaises(ValueError):
            run_feature({
                "companies": [],
                "contacts": [],
                "deals": [{"pk": 1, "title": "T", "stage": "bogus", "company_pk": None, "contact_pk": None}],
            })
        with self.assertRaises(ValueError):
            run_feature({
                "companies": [],
                "contacts": [],
                "deals": [
                    {"pk": 1, "title": "A", "stage": "new", "company_pk": None, "contact_pk": None},
                    {"pk": 1, "title": "B", "stage": "new", "company_pk": None, "contact_pk": None},
                ],
            })

    def test_inputs_not_mutated(self):
        payload = {
            "companies": [{"pk": 1, "name": "Acme"}],
            "contacts": [{"pk": 10, "name": "Marina", "company_pk": 1}],
            "deals": [{"pk": 100, "title": "Site", "stage": "new", "company_pk": 1, "contact_pk": 10}],
        }
        snapshot = copy.deepcopy(payload)
        run_feature(payload)
        self.assertEqual(payload, snapshot)
        bad = {
            "companies": [{"pk": 0, "name": "Acme"}],
            "contacts": [],
            "deals": [],
        }
        bad_snapshot = copy.deepcopy(bad)
        with self.assertRaises(ValueError):
            run_feature(bad)
        self.assertEqual(bad, bad_snapshot)

    def test_deterministic(self):
        payload = {
            "companies": [{"pk": 1, "name": "Acme"}],
            "contacts": [{"pk": 10, "name": "Marina", "company_pk": 1}],
            "deals": [{"pk": 100, "title": "Site", "stage": "new", "company_pk": 1, "contact_pk": 10}],
        }
        first = run_feature(copy.deepcopy(payload))
        second = run_feature(copy.deepcopy(payload))
        self.assertEqual(first, second)
