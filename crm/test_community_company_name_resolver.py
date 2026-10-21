import copy
import unittest
from crm.features.company_name_resolver import run_feature


class CompanyNameResolverCommunityTest(unittest.TestCase):
    def test_contract_example_resolved_and_empty(self):
        payload = {"companies": [{"name": "Padaria Sol", "pk": 1}], "rows": [{"company": "Padaria Sol", "line": 2}, {"company": "", "line": 3}]}
        out = run_feature(payload)
        self.assertEqual(out["total_count"], 2)
        self.assertEqual(out["resolved_count"], 1)
        self.assertEqual(out["empty_count"], 1)
        self.assertEqual(out["missing_count"], 0)
        self.assertEqual(out["ambiguous_count"], 0)
        self.assertTrue(out["can_import"])
        self.assertEqual(out["results"], [{"line": 2, "company": "Padaria Sol", "status": "resolved", "company_pk": 1}, {"line": 3, "company": "", "status": "empty", "company_pk": None}])

    def test_contract_example_ambiguous(self):
        payload = {"companies": [{"name": "Mercado", "pk": 1}, {"name": "Mercado", "pk": 2}], "rows": [{"company": "Mercado", "line": 2}]}
        out = run_feature(payload)
        self.assertEqual(out["ambiguous_count"], 1)
        self.assertFalse(out["can_import"])
        self.assertEqual(out["results"][0]["status"], "ambiguous")
        self.assertIsNone(out["results"][0]["company_pk"])

    def test_contract_example_case_sensitive_missing(self):
        payload = {"companies": [{"name": "Acme", "pk": 5}], "rows": [{"company": "acme", "line": 2}, {"company": "Desconhecida", "line": 3}]}
        out = run_feature(payload)
        self.assertEqual(out["missing_count"], 2)
        self.assertEqual(out["resolved_count"], 0)
        self.assertFalse(out["can_import"])
        for r in out["results"]:
            self.assertEqual(r["status"], "missing")
            self.assertIsNone(r["company_pk"])

    def test_defaults_empty_payload(self):
        out = run_feature({})
        self.assertEqual(out, {"total_count": 0, "resolved_count": 0, "empty_count": 0, "missing_count": 0, "ambiguous_count": 0, "can_import": True, "results": []})

    def test_extra_keys_ignored(self):
        payload = {"companies": [{"pk": 1, "name": "Sol", "owner": 99}], "rows": [{"line": 2, "company": "Sol", "extra": 1}], "other": 5}
        out = run_feature(payload)
        self.assertEqual(out["resolved_count"], 1)
        self.assertTrue(out["can_import"])

    def test_no_trim_or_casefold(self):
        payload = {"companies": [{"pk": 1, "name": "Acme"}], "rows": [{"line": 2, "company": " Acme"}, {"line": 3, "company": "Acme "}, {"line": 4, "company": "ACME"}, {"line": 5, "company": "Acme"}]}
        out = run_feature(payload)
        self.assertEqual([r["status"] for r in out["results"]], ["missing", "missing", "missing", "resolved"])
        self.assertEqual(out["resolved_count"], 1)
        self.assertEqual(out["missing_count"], 3)
        self.assertFalse(out["can_import"])

    def test_same_pk_duplicate_name_is_resolved(self):
        payload = {"companies": [{"pk": 7, "name": "Dup"}, {"pk": 7, "name": "Dup"}], "rows": [{"line": 2, "company": "Dup"}]}
        out = run_feature(payload)
        self.assertEqual(out["results"][0]["status"], "resolved")
        self.assertEqual(out["results"][0]["company_pk"], 7)
        self.assertTrue(out["can_import"])

    def test_preserves_input_order(self):
        payload = {"companies": [{"pk": 1, "name": "A"}, {"pk": 2, "name": "B"}], "rows": [{"line": 5, "company": "B"}, {"line": 2, "company": ""}, {"line": 9, "company": "ZZZ"}]}
        out = run_feature(payload)
        self.assertEqual([r["line"] for r in out["results"]], [5, 2, 9])
        self.assertEqual([r["status"] for r in out["results"]], ["resolved", "empty", "missing"])

    def test_counts_and_can_import(self):
        payload = {"companies": [{"pk": 1, "name": "A"}, {"pk": 2, "name": "B"}, {"pk": 3, "name": "B"}], "rows": [{"line": 2, "company": "A"}, {"line": 3, "company": ""}, {"line": 4, "company": "Missing"}, {"line": 5, "company": "B"}]}
        out = run_feature(payload)
        self.assertEqual(out["total_count"], 4)
        self.assertEqual(out["resolved_count"], 1)
        self.assertEqual(out["empty_count"], 1)
        self.assertEqual(out["missing_count"], 1)
        self.assertEqual(out["ambiguous_count"], 1)
        self.assertFalse(out["can_import"])

    def test_can_import_true_with_only_resolved_and_empty(self):
        payload = {"companies": [{"pk": 1, "name": "A"}], "rows": [{"line": 2, "company": "A"}, {"line": 3, "company": ""}]}
        self.assertTrue(run_feature(payload)["can_import"])
        payload2 = {"companies": [], "rows": [{"line": 2, "company": ""}]}
        self.assertTrue(run_feature(payload2)["can_import"])

    def test_does_not_mutate_inputs(self):
        payload = {"companies": [{"pk": 1, "name": "A"}], "rows": [{"line": 2, "company": "A"}, {"line": 3, "company": ""}]}
        snapshot = copy.deepcopy(payload)
        out = run_feature(payload)
        self.assertEqual(payload, snapshot)
        out["results"][0]["company"] = "MUT"
        out["results"].append({"line": 99, "company": "X", "status": "missing", "company_pk": None})
        self.assertEqual(payload, snapshot)

    def test_does_not_mutate_on_error(self):
        payload = {"companies": [{"pk": 1, "name": "A"}], "rows": [{"line": 2, "company": "A"}, {"line": 2, "company": "A"}]}
        snapshot = copy.deepcopy(payload)
        with self.assertRaises(ValueError):
            run_feature(payload)
        self.assertEqual(payload, snapshot)

    def test_deterministic(self):
        payload = {"companies": [{"pk": 1, "name": "A"}], "rows": [{"line": 2, "company": "A"}]}
        self.assertEqual(run_feature(payload), run_feature(payload))

    def test_rejects_non_object_payload(self):
        for bad in [None, [], "x", 5, True, 3.5]:
            with self.assertRaises(ValueError):
                run_feature(bad)

    def test_rejects_non_list_companies_rows(self):
        with self.assertRaises(ValueError):
            run_feature({"companies": {}, "rows": []})
        with self.assertRaises(ValueError):
            run_feature({"companies": [], "rows": "x"})
        with self.assertRaises(ValueError):
            run_feature({"companies": None, "rows": []})

    def test_rejects_oversized_lists(self):
        companies = [{"pk": i + 1, "name": "C%d" % i} for i in range(2001)]
        with self.assertRaises(ValueError):
            run_feature({"companies": companies, "rows": []})
        rows = [{"line": i + 2, "company": ""} for i in range(501)]
        with self.assertRaises(ValueError):
            run_feature({"companies": [], "rows": rows})

    def test_rejects_bad_pk_and_name(self):
        with self.assertRaises(ValueError):
            run_feature({"companies": [{"pk": True, "name": "A"}], "rows": []})
        with self.assertRaises(ValueError):
            run_feature({"companies": [{"pk": 0, "name": "A"}], "rows": []})
        with self.assertRaises(ValueError):
            run_feature({"companies": [{"pk": "1", "name": "A"}], "rows": []})
        with self.assertRaises(ValueError):
            run_feature({"companies": [{"pk": 1, "name": ""}], "rows": []})
        with self.assertRaises(ValueError):
            run_feature({"companies": [{"pk": 1, "name": "x" * 181}], "rows": []})
        with self.assertRaises(ValueError):
            run_feature({"companies": [{"pk": 1}], "rows": []})
        with self.assertRaises(ValueError):
            run_feature({"companies": ["x"], "rows": []})

    def test_rejects_bad_rows(self):
        with self.assertRaises(ValueError):
            run_feature({"companies": [], "rows": [{"line": True, "company": ""}]})
        with self.assertRaises(ValueError):
            run_feature({"companies": [], "rows": [{"line": 1, "company": ""}]})
        with self.assertRaises(ValueError):
            run_feature({"companies": [], "rows": [{"line": "2", "company": ""}]})
        with self.assertRaises(ValueError):
            run_feature({"companies": [], "rows": [{"line": 2, "company": "x" * 181}]})
        with self.assertRaises(ValueError):
            run_feature({"companies": [], "rows": [{"line": 2}]})
        with self.assertRaises(ValueError):
            run_feature({"companies": [], "rows": ["x"]})

    def test_rejects_duplicate_lines(self):
        with self.assertRaises(ValueError):
            run_feature({"companies": [], "rows": [{"line": 2, "company": ""}, {"line": 2, "company": ""}]})


if __name__ == "__main__":
    unittest.main()
