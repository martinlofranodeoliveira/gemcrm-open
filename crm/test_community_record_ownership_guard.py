import copy
import unittest

from crm.features.record_ownership_guard import run_feature


class RecordOwnershipGuardTest(unittest.TestCase):
    def test_empty_records_default(self):
        result = run_feature({"owner": 3})
        self.assertEqual(result, {
            "owner": 3,
            "total_count": 0,
            "owned_count": 0,
            "isolated_count": 0,
            "accessible_count": 0,
            "results": [],
        })

    def test_company_contact_example(self):
        payload = {
            "owner": 7,
            "records": [
                {"kind": "company", "owner": 7, "pk": 1},
                {"company_owner": 7, "kind": "contact", "owner": 7, "pk": 2},
                {"company_owner": 9, "kind": "contact", "owner": 7, "pk": 3},
            ],
        }
        result = run_feature(payload)
        self.assertEqual(result["owner"], 7)
        self.assertEqual(result["total_count"], 3)
        self.assertEqual(result["owned_count"], 3)
        self.assertEqual(result["isolated_count"], 2)
        self.assertEqual(result["accessible_count"], 2)
        self.assertEqual(result["results"][0], {
            "kind": "company", "pk": 1, "owner": 7,
            "company_owner": None, "contact_owner": None, "deal_owner": None,
            "owned": True, "isolated": True, "accessible": True,
        })
        self.assertEqual(result["results"][1]["accessible"], True)
        self.assertEqual(result["results"][2]["accessible"], False)
        self.assertEqual(result["results"][2]["isolated"], False)

    def test_deal_task_example(self):
        payload = {
            "owner": 5,
            "records": [
                {"company_owner": 5, "contact_owner": None, "kind": "deal", "owner": 5, "pk": 10},
                {"deal_owner": 9, "kind": "task", "owner": 9, "pk": 11},
            ],
        }
        result = run_feature(payload)
        self.assertEqual(result["total_count"], 2)
        self.assertEqual(result["owned_count"], 1)
        self.assertEqual(result["isolated_count"], 2)
        self.assertEqual(result["accessible_count"], 1)
        self.assertTrue(result["results"][0]["accessible"])
        self.assertTrue(result["results"][1]["isolated"])
        self.assertFalse(result["results"][1]["owned"])
        self.assertFalse(result["results"][1]["accessible"])

    def test_deterministic_equal_output(self):
        payload = {
            "owner": 7,
            "records": [
                {"kind": "company", "owner": 7, "pk": 1},
                {"company_owner": 7, "kind": "contact", "owner": 7, "pk": 2},
            ],
        }
        first = run_feature(payload)
        second = run_feature(payload)
        self.assertEqual(first, second)
        self.assertIsNot(first, second)
        self.assertIsNot(first["results"], second["results"])

    def test_does_not_mutate_inputs(self):
        payload = {
            "owner": 7,
            "records": [
                {"kind": "contact", "owner": 7, "pk": 2},
                {"kind": "deal", "owner": 7, "pk": 3, "company_owner": 7},
            ],
        }
        snapshot = copy.deepcopy(payload)
        run_feature(payload)
        self.assertEqual(payload, snapshot)

    def test_extra_keys_ignored(self):
        result = run_feature({
            "owner": 4, "extra": "ignored",
            "records": [{"kind": "company", "owner": 4, "pk": 1, "note": "x"}],
        })
        self.assertEqual(result["total_count"], 1)
        self.assertEqual(result["accessible_count"], 1)

    def test_missing_links_normalized_to_none(self):
        result = run_feature({"owner": 4, "records": [{"kind": "task", "owner": 4, "pk": 1}]})
        entry = result["results"][0]
        self.assertIsNone(entry["company_owner"])
        self.assertIsNone(entry["contact_owner"])
        self.assertIsNone(entry["deal_owner"])
        self.assertTrue(entry["isolated"])
        self.assertTrue(entry["accessible"])

    def test_owner_validation(self):
        with self.assertRaises(ValueError):
            run_feature({})
        with self.assertRaises(ValueError):
            run_feature({"owner": True})
        with self.assertRaises(ValueError):
            run_feature({"owner": 0})
        with self.assertRaises(ValueError):
            run_feature({"owner": 9007199254740992})
        with self.assertRaises(ValueError):
            run_feature({"owner": "7"})
        with self.assertRaises(ValueError):
            run_feature({"owner": 7.0})
        with self.assertRaises(ValueError):
            run_feature([])
        with self.assertRaises(ValueError):
            run_feature(None)

    def test_records_must_be_list_and_limited(self):
        with self.assertRaises(ValueError):
            run_feature({"owner": 1, "records": {}})
        with self.assertRaises(ValueError):
            run_feature({"owner": 1, "records": None})
        many = [{"kind": "company", "owner": 1, "pk": i + 1} for i in range(5001)]
        with self.assertRaises(ValueError):
            run_feature({"owner": 1, "records": many})

    def test_record_field_validation(self):
        with self.assertRaises(ValueError):
            run_feature({"owner": 1, "records": [{"owner": 1, "pk": 1}]})
        with self.assertRaises(ValueError):
            run_feature({"owner": 1, "records": [{"kind": "lead", "owner": 1, "pk": 1}]})
        with self.assertRaises(ValueError):
            run_feature({"owner": 1, "records": [{"kind": "company", "owner": 1, "pk": True}]})
        with self.assertRaises(ValueError):
            run_feature({"owner": 1, "records": [{"kind": "company", "owner": False, "pk": 1}]})
        with self.assertRaises(ValueError):
            run_feature({"owner": 1, "records": ["nope"]})
        with self.assertRaises(ValueError):
            run_feature({"owner": 1, "records": [{"kind": "company", "owner": 1, "pk": 0}]})

    def test_link_type_validation(self):
        with self.assertRaises(ValueError):
            run_feature({"owner": 1, "records": [{"kind": "contact", "owner": 1, "pk": 1, "company_owner": True}]})
        with self.assertRaises(ValueError):
            run_feature({"owner": 1, "records": [{"kind": "contact", "owner": 1, "pk": 1, "company_owner": "1"}]})
        with self.assertRaises(ValueError):
            run_feature({"owner": 1, "records": [{"kind": "deal", "owner": 1, "pk": 1, "company_owner": 0}]})
        with self.assertRaises(ValueError):
            run_feature({"owner": 1, "records": [{"kind": "task", "owner": 1, "pk": 1, "deal_owner": False}]})

    def test_company_allows_no_links(self):
        with self.assertRaises(ValueError):
            run_feature({"owner": 1, "records": [{"kind": "company", "owner": 1, "pk": 1, "company_owner": 1}]})
        with self.assertRaises(ValueError):
            run_feature({"owner": 1, "records": [{"kind": "company", "owner": 1, "pk": 1, "contact_owner": 1}]})
        with self.assertRaises(ValueError):
            run_feature({"owner": 1, "records": [{"kind": "company", "owner": 1, "pk": 1, "deal_owner": 1}]})

    def test_contact_only_company_owner(self):
        run_feature({"owner": 1, "records": [{"kind": "contact", "owner": 1, "pk": 1, "company_owner": 1}]})
        with self.assertRaises(ValueError):
            run_feature({"owner": 1, "records": [{"kind": "contact", "owner": 1, "pk": 1, "contact_owner": 1}]})
        with self.assertRaises(ValueError):
            run_feature({"owner": 1, "records": [{"kind": "contact", "owner": 1, "pk": 1, "deal_owner": 1}]})

    def test_deal_allows_company_and_contact_only(self):
        run_feature({"owner": 1, "records": [{"kind": "deal", "owner": 1, "pk": 1, "company_owner": 1, "contact_owner": 1}]})
        with self.assertRaises(ValueError):
            run_feature({"owner": 1, "records": [{"kind": "deal", "owner": 1, "pk": 1, "deal_owner": 1}]})

    def test_task_only_deal_owner(self):
        run_feature({"owner": 1, "records": [{"kind": "task", "owner": 1, "pk": 1, "deal_owner": 1}]})
        with self.assertRaises(ValueError):
            run_feature({"owner": 1, "records": [{"kind": "task", "owner": 1, "pk": 1, "company_owner": 1}]})
        with self.assertRaises(ValueError):
            run_feature({"owner": 1, "records": [{"kind": "task", "owner": 1, "pk": 1, "contact_owner": 1}]})

    def test_foreign_owner_isolated_when_links_match_record(self):
        result = run_feature({"owner": 5, "records": [{"kind": "task", "owner": 9, "pk": 11, "deal_owner": 9}]})
        entry = result["results"][0]
        self.assertFalse(entry["owned"])
        self.assertTrue(entry["isolated"])
        self.assertFalse(entry["accessible"])
        self.assertEqual(result["owned_count"], 0)
        self.assertEqual(result["isolated_count"], 1)
        self.assertEqual(result["accessible_count"], 0)

    def test_cross_owner_link_not_isolated_or_accessible(self):
        result = run_feature({"owner": 7, "records": [{"kind": "contact", "owner": 7, "pk": 3, "company_owner": 9}]})
        entry = result["results"][0]
        self.assertTrue(entry["owned"])
        self.assertFalse(entry["isolated"])
        self.assertFalse(entry["accessible"])

    def test_order_and_counts(self):
        payload = {
            "owner": 2,
            "records": [
                {"kind": "company", "owner": 2, "pk": 30},
                {"kind": "company", "owner": 8, "pk": 31},
                {"kind": "contact", "owner": 2, "pk": 32, "company_owner": 8},
            ],
        }
        result = run_feature(payload)
        self.assertEqual([r["pk"] for r in result["results"]], [30, 31, 32])
        self.assertEqual(result["total_count"], 3)
        self.assertEqual(result["owned_count"], 2)
        self.assertEqual(result["isolated_count"], 2)
        self.assertEqual(result["accessible_count"], 1)


if __name__ == "__main__":
    unittest.main()
