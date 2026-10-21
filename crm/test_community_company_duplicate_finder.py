import copy
import unittest

from crm.features.company_duplicate_finder import run_feature


class CompanyDuplicateFinderTests(unittest.TestCase):
    def test_missing_companies_defaults_empty(self):
        self.assertEqual(run_feature({}), {"group_count": 0, "groups": []})
        self.assertEqual(run_feature({"extra": 1}), {"group_count": 0, "groups": []})

    def test_basic_example(self):
        payload = {"companies": [{"name": "Acme", "pk": 1}, {"name": " acme ", "pk": 2}, {"name": "Beta", "pk": 3}]}
        result = run_feature(payload)
        self.assertEqual(result, {"group_count": 1, "groups": [{"key": "acme", "count": 2, "companies": [{"pk": 1, "name": "Acme"}, {"pk": 2, "name": " acme "}]}]})

    def test_no_duplicates(self):
        payload = {"companies": [{"name": "Padaria", "pk": 1}, {"name": "Mercado", "pk": 2}]}
        self.assertEqual(run_feature(payload), {"group_count": 0, "groups": []})

    def test_casefold_unicode(self):
        payload = {"companies": [{"name": "S\u00c3O PAULO", "pk": 5}, {"name": "s\u00e3o paulo", "pk": 6}]}
        result = run_feature(payload)
        self.assertEqual(result["group_count"], 1)
        self.assertEqual(result["groups"][0]["key"], "s\u00e3o paulo")
        self.assertEqual(result["groups"][0]["count"], 2)

    def test_strips_space_tab_lf_cr(self):
        payload = {"companies": [{"name": "Acme", "pk": 1}, {"name": " \t\n\rAcMe \r\n\t ", "pk": 2}]}
        result = run_feature(payload)
        self.assertEqual(result["group_count"], 1)
        self.assertEqual(result["groups"][0]["key"], "acme")
        self.assertEqual(result["groups"][0]["companies"][0], {"pk": 1, "name": "Acme"})
        self.assertEqual(result["groups"][0]["companies"][1], {"pk": 2, "name": " \t\n\rAcMe \r\n\t "})

    def test_keeps_only_groups_larger_than_one(self):
        payload = {"companies": [{"name": "A", "pk": 1}, {"name": "a", "pk": 2}, {"name": "B", "pk": 3}]}
        result = run_feature(payload)
        self.assertEqual(result["group_count"], 1)
        self.assertEqual(len(result["groups"]), 1)
        self.assertEqual(result["groups"][0]["key"], "a")

    def test_sorts_groups_by_key_and_members_by_pk(self):
        payload = {"companies": [{"name": "beta", "pk": 10}, {"name": "Beta ", "pk": 3}, {"name": "alpha", "pk": 9}, {"name": " ALPHA", "pk": 4}]}
        result = run_feature(payload)
        self.assertEqual(result["group_count"], 2)
        self.assertEqual(result["groups"][0]["key"], "alpha")
        self.assertEqual(result["groups"][1]["key"], "beta")
        self.assertEqual([c["pk"] for c in result["groups"][0]["companies"]], [4, 9])
        self.assertEqual([c["pk"] for c in result["groups"][1]["companies"]], [3, 10])

    def test_group_count_matches_groups_length(self):
        result = run_feature({"companies": [{"name": "X", "pk": 1}, {"name": "x", "pk": 2}]})
        self.assertEqual(result["group_count"], len(result["groups"]))

    def test_extra_keys_ignored(self):
        payload = {"companies": [{"pk": 1, "name": "Acme", "owner": 99}, {"pk": 2, "name": "acme", "foo": "bar"}], "other": True}
        result = run_feature(payload)
        self.assertEqual(result["group_count"], 1)
        self.assertEqual(result["groups"][0]["companies"], [{"pk": 1, "name": "Acme"}, {"pk": 2, "name": "acme"}])

    def test_does_not_mutate_inputs(self):
        payload = {"companies": [{"name": "Acme", "pk": 2}, {"name": " acme", "pk": 1}], "extra": [1]}
        snapshot = copy.deepcopy(payload)
        run_feature(payload)
        self.assertEqual(payload, snapshot)

    def test_deterministic(self):
        payload = {"companies": [{"name": "Acme", "pk": 1}, {"name": "ACME", "pk": 2}]}
        first = run_feature(payload)
        second = run_feature(payload)
        self.assertEqual(first, second)
        self.assertIsNot(first, second)

    def test_rejects_non_object_payload(self):
        for bad in [None, True, False, 1, "x", [], [1], (1,)]:
            with self.assertRaises(ValueError):
                run_feature(bad)

    def test_rejects_non_list_companies(self):
        for bad in [None, "x", 1, True, {}, (1,)]:
            with self.assertRaises(ValueError):
                run_feature({"companies": bad})

    def test_rejects_oversized_list(self):
        companies = []
        for i in range(5001):
            companies.append({"pk": i + 1, "name": "N" + str(i + 1)})
        with self.assertRaises(ValueError):
            run_feature({"companies": companies})

    def test_rejects_non_object_entries(self):
        for bad in [None, 1, "x", [], True]:
            with self.assertRaises(ValueError):
                run_feature({"companies": [bad]})

    def test_rejects_bad_pk(self):
        for bad in [True, False, "1", 1.0, None, 0, -1, 9007199254740992]:
            with self.assertRaises(ValueError):
                run_feature({"companies": [{"pk": bad, "name": "Acme"}]})
        with self.assertRaises(ValueError):
            run_feature({"companies": [{"name": "Acme"}]})

    def test_pk_boundaries_ok(self):
        result = run_feature({"companies": [{"pk": 1, "name": "A"}, {"pk": 9007199254740991, "name": "B"}]})
        self.assertEqual(result, {"group_count": 0, "groups": []})

    def test_rejects_bad_name(self):
        with self.assertRaises(ValueError):
            run_feature({"companies": [{"pk": 1}]})
        for bad in [None, 1, True, b"x"]:
            with self.assertRaises(ValueError):
                run_feature({"companies": [{"pk": 1, "name": bad}]})
        with self.assertRaises(ValueError):
            run_feature({"companies": [{"pk": 1, "name": "x" * 181}]})
        result = run_feature({"companies": [{"pk": 1, "name": "x" * 180}]})
        self.assertEqual(result, {"group_count": 0, "groups": []})

    def test_rejects_empty_trimmed_name(self):
        for bad in ["", "   ", " \t\n\r "]:
            with self.assertRaises(ValueError):
                run_feature({"companies": [{"pk": 1, "name": bad}]})

    def test_rejects_duplicate_pk(self):
        with self.assertRaises(ValueError):
            run_feature({"companies": [{"pk": 1, "name": "A"}, {"pk": 1, "name": "B"}]})


if __name__ == "__main__":
    unittest.main()
