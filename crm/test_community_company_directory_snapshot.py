import copy
import unittest

from crm.features.company_directory_snapshot import run_feature


class CompanyDirectorySnapshotTests(unittest.TestCase):
    def test_defaults_and_empty_store(self):
        out = run_feature({})
        self.assertEqual(out, {"q": "", "total_count": 0, "results": []})
        out2 = run_feature({"companies": [], "contacts": [], "deals": [], "q": None})
        self.assertEqual(out2, {"q": "", "total_count": 0, "results": []})

    def test_contract_example_search(self):
        payload = {
            "companies": [{"name": "Padaria Sol", "pk": 2}, {"name": "Mercado Lima", "pk": 1}],
            "contacts": [{"company_pk": 1, "pk": 10}, {"company_pk": 1, "pk": 11}, {"company_pk": 2, "pk": 12}],
            "deals": [{"company_pk": 1, "pk": 5}],
            "q": "  mercado ",
        }
        out = run_feature(payload)
        self.assertEqual(out, {
            "q": "mercado",
            "total_count": 1,
            "results": [{"contact_count": 2, "deal_count": 1, "name": "Mercado Lima", "pk": 1}],
        })

    def test_contract_example_sort(self):
        payload = {
            "companies": [{"name": "Beta", "pk": 1}, {"name": "Alfa", "pk": 2}],
            "contacts": [],
            "deals": [],
            "q": None,
        }
        out = run_feature(payload)
        self.assertEqual(out["q"], "")
        self.assertEqual(out["total_count"], 2)
        self.assertEqual([r["name"] for r in out["results"]], ["Alfa", "Beta"])

    def test_search_casefold_and_whitespace(self):
        payload = {
            "companies": [{"pk": 1, "name": "MERCADO Lima"}, {"pk": 2, "name": "Padaria"}],
            "q": "  mercado ",
        }
        out = run_feature(payload)
        self.assertEqual(out["q"], "mercado")
        self.assertEqual(len(out["results"]), 1)
        self.assertEqual(out["results"][0]["pk"], 1)

    def test_search_matches_name_only_and_substring(self):
        payload = {
            "companies": [{"pk": 1, "name": "Alfa"}, {"pk": 2, "name": "Beta Alfa"}],
            "q": "alfa",
        }
        out = run_feature(payload)
        self.assertEqual([r["pk"] for r in out["results"]], [1, 2])

    def test_sort_name_codepoint_then_pk(self):
        payload = {
            "companies": [
                {"pk": 3, "name": "b"},
                {"pk": 1, "name": "Same"},
                {"pk": 2, "name": "Same"},
                {"pk": 4, "name": "A"},
            ]
        }
        out = run_feature(payload)
        self.assertEqual([r["name"] for r in out["results"]], ["A", "Same", "Same", "b"])
        self.assertEqual([r["pk"] for r in out["results"]], [4, 1, 2, 3])

    def test_counts_by_equality_missing_none(self):
        payload = {
            "companies": [{"pk": 1, "name": "A"}, {"pk": 2, "name": "B"}],
            "contacts": [{"pk": 10, "company_pk": 1}, {"pk": 11}, {"pk": 12, "company_pk": None}],
            "deals": [{"pk": 20, "company_pk": 2}, {"pk": 21, "company_pk": 99}],
        }
        out = run_feature(payload)
        by_pk = {r["pk"]: r for r in out["results"]}
        self.assertEqual(by_pk[1]["contact_count"], 1)
        self.assertEqual(by_pk[1]["deal_count"], 0)
        self.assertEqual(by_pk[2]["contact_count"], 0)
        self.assertEqual(by_pk[2]["deal_count"], 1)

    def test_oversized_q_truncated_not_rejected(self):
        long_q = "  " + ("x" * 500) + "  "
        out = run_feature({"companies": [], "q": long_q})
        self.assertEqual(len(out["q"]), 200)
        self.assertEqual(out["q"], "x" * 200)

    def test_malformed_raise(self):
        with self.assertRaises(ValueError):
            run_feature(None)
        with self.assertRaises(ValueError):
            run_feature([])
        with self.assertRaises(ValueError):
            run_feature({"companies": {}})
        with self.assertRaises(ValueError):
            run_feature({"companies": [{"pk": True, "name": "A"}]})
        with self.assertRaises(ValueError):
            run_feature({"companies": [{"pk": 1, "name": ""}]})
        with self.assertRaises(ValueError):
            run_feature({"companies": [{"pk": 0, "name": "A"}]})
        with self.assertRaises(ValueError):
            run_feature({"contacts": [{"pk": 1, "company_pk": True}]})
        with self.assertRaises(ValueError):
            run_feature({"deals": [{"pk": 1, "company_pk": 0}]})
        with self.assertRaises(ValueError):
            run_feature({"q": 123})
        with self.assertRaises(ValueError):
            run_feature({"companies": [{"pk": 1}]})
        with self.assertRaises(ValueError):
            run_feature({"companies": [{"pk": 1, "name": "A" * 181}]})

    def test_over_limit_lists_raise(self):
        big = [{"pk": i + 1, "name": "A"} for i in range(2001)]
        with self.assertRaises(ValueError):
            run_feature({"companies": big})
        with self.assertRaises(ValueError):
            run_feature({"contacts": big})
        with self.assertRaises(ValueError):
            run_feature({"deals": big})

    def test_no_mutation_and_deterministic(self):
        payload = {
            "companies": [{"pk": 2, "name": "Beta"}, {"pk": 1, "name": "Alfa"}],
            "contacts": [{"pk": 10, "company_pk": 1}],
            "deals": [],
            "q": "a",
        }
        snapshot = copy.deepcopy(payload)
        first = run_feature(payload)
        second = run_feature(payload)
        self.assertEqual(first, second)
        self.assertEqual(payload, snapshot)

    def test_extra_keys_ignored(self):
        payload = {
            "companies": [{"pk": 1, "name": "Alfa", "owner": "x"}],
            "contacts": [{"pk": 5, "company_pk": 1, "extra": 1}],
            "deals": [{"pk": 6, "company_pk": 1, "extra": 2}],
            "q": None,
            "other": 123,
        }
        out = run_feature(payload)
        self.assertEqual(out["total_count"], 1)
        self.assertEqual(out["results"][0], {"pk": 1, "name": "Alfa", "contact_count": 1, "deal_count": 1})
