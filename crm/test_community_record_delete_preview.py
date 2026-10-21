import copy
import unittest

from crm.features.record_delete_preview import run_feature


class RecordDeletePreviewTest(unittest.TestCase):
    def test_company_target(self):
        payload = {
            "target": {"kind": "company", "pk": 7},
            "contacts": [
                {"pk": 1, "company_pk": 7},
                {"pk": 2, "company_pk": 8},
                {"pk": 3, "company_pk": None},
            ],
            "deals": [
                {"pk": 10, "company_pk": 7, "contact_pk": None},
                {"pk": 11, "company_pk": 8, "contact_pk": None},
            ],
            "tasks": [{"pk": 20, "deal_pk": 10}],
        }
        result = run_feature(payload)
        self.assertEqual(result["target"], {"kind": "company", "pk": 7})
        self.assertEqual(result["affected"], {"contacts": [1], "deals": [10], "tasks": []})
        self.assertEqual(result["counts"], {"contacts": 1, "deals": 1, "tasks": 0, "total": 2})
        self.assertTrue(result["preserves_linked"] is True)

    def test_company_sorts_numeric_and_dedupes(self):
        payload = {
            "target": {"kind": "company", "pk": 5},
            "contacts": [
                {"pk": 10, "company_pk": 5},
                {"pk": 2, "company_pk": 5},
                {"pk": 2, "company_pk": 5},
            ],
            "deals": [
                {"pk": 30, "company_pk": 5, "contact_pk": None},
                {"pk": 9, "company_pk": 5, "contact_pk": None},
            ],
            "tasks": [],
        }
        result = run_feature(payload)
        self.assertEqual(result["affected"]["contacts"], [2, 10])
        self.assertEqual(result["affected"]["deals"], [9, 30])
        self.assertEqual(result["counts"]["total"], 4)

    def test_contact_target(self):
        payload = {
            "target": {"kind": "contact", "pk": 3},
            "contacts": [],
            "deals": [
                {"pk": 10, "company_pk": None, "contact_pk": 3},
                {"pk": 11, "company_pk": None, "contact_pk": 4},
            ],
            "tasks": [],
        }
        result = run_feature(payload)
        self.assertEqual(result["affected"], {"contacts": [], "deals": [10], "tasks": []})
        self.assertEqual(result["counts"], {"contacts": 0, "deals": 1, "tasks": 0, "total": 1})
        self.assertTrue(result["preserves_linked"] is True)

    def test_deal_target(self):
        payload = {
            "target": {"kind": "deal", "pk": 10},
            "contacts": [],
            "deals": [],
            "tasks": [
                {"pk": 20, "deal_pk": 10},
                {"pk": 21, "deal_pk": 11},
                {"pk": 22, "deal_pk": None},
            ],
        }
        result = run_feature(payload)
        self.assertEqual(result["affected"], {"contacts": [], "deals": [], "tasks": [20]})
        self.assertEqual(result["counts"], {"contacts": 0, "deals": 0, "tasks": 1, "total": 1})
        self.assertTrue(result["preserves_linked"] is True)

    def test_task_target_empty(self):
        payload = {
            "target": {"kind": "task", "pk": 20},
            "contacts": [{"pk": 1, "company_pk": 7}],
            "deals": [{"pk": 10, "company_pk": 7, "contact_pk": 1}],
            "tasks": [{"pk": 20, "deal_pk": 10}],
        }
        result = run_feature(payload)
        self.assertEqual(result["affected"], {"contacts": [], "deals": [], "tasks": []})
        self.assertEqual(result["counts"], {"contacts": 0, "deals": 0, "tasks": 0, "total": 0})
        self.assertTrue(result["preserves_linked"] is True)

    def test_missing_fk_means_none(self):
        payload = {
            "target": {"kind": "company", "pk": 7},
            "contacts": [{"pk": 1}],
            "deals": [{"pk": 10}],
            "tasks": [{"pk": 20}],
        }
        result = run_feature(payload)
        self.assertEqual(result["affected"], {"contacts": [], "deals": [], "tasks": []})
        self.assertEqual(result["counts"]["total"], 0)

    def test_extra_keys_ignored_and_defaults(self):
        result = run_feature({"target": {"kind": "task", "pk": 1, "extra": 2}, "other": 99})
        self.assertEqual(result["affected"], {"contacts": [], "deals": [], "tasks": []})
        self.assertEqual(result["counts"]["total"], 0)

    def test_malformed_inputs_raise(self):
        with self.assertRaises(ValueError):
            run_feature("nope")
        with self.assertRaises(ValueError):
            run_feature({})
        with self.assertRaises(ValueError):
            run_feature({"target": {"kind": "nope", "pk": 1}})
        with self.assertRaises(ValueError):
            run_feature({"target": {"kind": "company", "pk": True}})
        with self.assertRaises(ValueError):
            run_feature({"target": {"kind": "company", "pk": 0}})
        with self.assertRaises(ValueError):
            run_feature({"target": {"kind": "company", "pk": 9007199254740992}})
        with self.assertRaises(ValueError):
            run_feature({"target": {"kind": "company", "pk": 1}, "contacts": {}})
        with self.assertRaises(ValueError):
            run_feature({"target": {"kind": "company", "pk": 1}, "contacts": [{"pk": True}]})
        with self.assertRaises(ValueError):
            run_feature({"target": {"kind": "company", "pk": 1}, "contacts": [{"pk": 1, "company_pk": "7"}]})
        with self.assertRaises(ValueError):
            run_feature({"target": {"kind": "company", "pk": 1}, "deals": [{"pk": 1, "company_pk": False}]})
        with self.assertRaises(ValueError):
            run_feature({"target": {"kind": "deal", "pk": 1}, "tasks": [{"pk": 1, "deal_pk": 1.5}]})

    def test_limit_violation(self):
        big = [{"pk": i + 1} for i in range(2001)]
        with self.assertRaises(ValueError):
            run_feature({"target": {"kind": "company", "pk": 1}, "contacts": big})

    def test_inputs_never_mutated_and_deterministic(self):
        payload = {
            "target": {"kind": "company", "pk": 7},
            "contacts": [{"pk": 1, "company_pk": 7}],
            "deals": [{"pk": 10, "company_pk": 7, "contact_pk": None}],
            "tasks": [{"pk": 20, "deal_pk": 10}],
        }
        snapshot = copy.deepcopy(payload)
        first = run_feature(payload)
        second = run_feature(copy.deepcopy(snapshot))
        self.assertEqual(payload, snapshot)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
