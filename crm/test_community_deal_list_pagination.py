import copy
import unittest

from crm.features.deal_list_pagination import run_feature


class DealListPaginationTest(unittest.TestCase):
    def test_contract_example_sorted_all(self):
        payload = {
            "deals": [
                {"pk": 1, "stage": "new", "title": "Padaria"},
                {"pk": 2, "stage": "won", "title": "Mercado"},
            ],
            "page": 1,
            "q": "",
            "stage": "all",
        }
        out = run_feature(payload)
        self.assertEqual(out["q"], "")
        self.assertEqual(out["stage"], "all")
        self.assertEqual(out["page"], 1)
        self.assertEqual(out["per_page"], 50)
        self.assertEqual(out["num_pages"], 1)
        self.assertEqual(out["total_count"], 2)
        self.assertEqual(out["results"], [
            {"pk": 2, "stage": "won", "title": "Mercado"},
            {"pk": 1, "stage": "new", "title": "Padaria"},
        ])
        self.assertEqual(out["has_previous"], False)
        self.assertEqual(out["has_next"], False)
        self.assertEqual(out["prev_page"], None)
        self.assertEqual(out["next_page"], None)

    def test_contract_example_stage_and_query(self):
        payload = {
            "deals": [
                {"pk": 1, "stage": "new", "title": "Padaria Centro"},
                {"pk": 2, "stage": "qualified", "title": "Padaria Norte"},
                {"pk": 3, "stage": "new", "title": "Mercado Sul"},
            ],
            "page": 1,
            "q": "padaria",
            "stage": "new",
        }
        out = run_feature(payload)
        self.assertEqual(out["total_count"], 1)
        self.assertEqual(out["results"], [{"pk": 1, "stage": "new", "title": "Padaria Centro"}])
        self.assertEqual(out["q"], "padaria")
        self.assertEqual(out["stage"], "new")

    def test_contract_example_empty_clamps(self):
        out = run_feature({"deals": [], "page": 99, "q": "zzz", "stage": "all"})
        self.assertEqual(out["page"], 1)
        self.assertEqual(out["num_pages"], 1)
        self.assertEqual(out["total_count"], 0)
        self.assertEqual(out["results"], [])

    def test_filter_casefold_substring(self):
        deals = [
            {"pk": 1, "title": "PADARIA Centro", "stage": "new"},
            {"pk": 2, "title": "mercado sul", "stage": "new"},
        ]
        out = run_feature({"deals": deals, "q": "padaria", "stage": "all"})
        self.assertEqual(len(out["results"]), 1)
        self.assertEqual(out["results"][0]["pk"], 1)

    def test_stage_then_query_order(self):
        deals = [
            {"pk": 1, "title": "Padaria Centro", "stage": "new"},
            {"pk": 2, "title": "padaria centro", "stage": "qualified"},
            {"pk": 3, "title": "Padaria Centro", "stage": "new"},
        ]
        out = run_feature({"deals": deals, "q": "PADARIA", "stage": "new"})
        self.assertEqual(out["total_count"], 2)
        self.assertEqual([r["pk"] for r in out["results"]], [1, 3])

    def test_sort_casefold_title_pk(self):
        deals = [
            {"pk": 5, "title": "b", "stage": "new"},
            {"pk": 3, "title": "A", "stage": "new"},
            {"pk": 4, "title": "a", "stage": "new"},
        ]
        out = run_feature({"deals": deals})
        titles = [(r["title"], r["pk"]) for r in out["results"]]
        self.assertEqual(titles, [("A", 3), ("a", 4), ("b", 5)])

    def test_results_only_pk_title_stage_copies(self):
        deals = [{"pk": 1, "title": "T", "stage": "new", "extra": "x"}]
        out = run_feature({"deals": deals})
        self.assertEqual(out["results"], [{"pk": 1, "title": "T", "stage": "new"}])
        out["results"][0]["title"] = "CHANGED"
        self.assertEqual(deals[0]["title"], "T")

    def test_pagination_fifty_per_page(self):
        deals = []
        for i in range(55):
            deals.append({"pk": i + 1, "title": "T%03d" % (i + 1), "stage": "new"})
        p1 = run_feature({"deals": deals, "page": 1})
        p2 = run_feature({"deals": deals, "page": 2})
        self.assertEqual(p1["total_count"], 55)
        self.assertEqual(p1["num_pages"], 2)
        self.assertEqual(len(p1["results"]), 50)
        self.assertEqual(len(p2["results"]), 5)
        self.assertEqual(p1["has_next"], True)
        self.assertEqual(p1["next_page"], 2)
        self.assertEqual(p1["has_previous"], False)
        self.assertEqual(p1["prev_page"], None)
        self.assertEqual(p2["page"], 2)
        self.assertEqual(p2["has_previous"], True)
        self.assertEqual(p2["prev_page"], 1)
        self.assertEqual(p2["has_next"], False)
        self.assertEqual(p2["next_page"], None)

    def test_out_of_range_integers_clamp_to_last(self):
        deals = []
        for i in range(55):
            deals.append({"pk": i + 1, "title": "T%03d" % (i + 1), "stage": "new"})
        out_high = run_feature({"deals": deals, "page": 99})
        self.assertEqual(out_high["page"], 2)
        self.assertEqual(len(out_high["results"]), 5)
        out_low = run_feature({"deals": deals, "page": 0})
        self.assertEqual(out_low["page"], 2)
        out_neg = run_feature({"deals": deals, "page": -3})
        self.assertEqual(out_neg["page"], 2)

    def test_non_integer_page_resolves_first(self):
        deals = []
        for i in range(55):
            deals.append({"pk": i + 1, "title": "T%03d" % (i + 1), "stage": "new"})
        for bad in ["abc", "1.5", "--1", "-", "1a"]:
            out = run_feature({"deals": deals, "page": bad})
            self.assertEqual(out["page"], 1, msg=bad)
            self.assertEqual(len(out["results"]), 50, msg=bad)

    def test_page_string_parsing(self):
        deals = []
        for i in range(55):
            deals.append({"pk": i + 1, "title": "T%03d" % (i + 1), "stage": "new"})
        self.assertEqual(run_feature({"deals": deals, "page": " 2 "})["page"], 2)
        self.assertEqual(run_feature({"deals": deals, "page": ""})["page"], 1)
        self.assertEqual(run_feature({"deals": deals, "page": " \t\n\r "})["page"], 1)
        self.assertEqual(run_feature({"deals": []})["page"], 1)
        self.assertEqual(run_feature({"deals": [], "page": None})["page"], 1)

    def test_q_normalization(self):
        out = run_feature({"deals": [], "q": " \t hi \n\r"})
        self.assertEqual(out["q"], "hi")
        long_q = "  " + ("x" * 300) + "  "
        out2 = run_feature({"deals": [], "q": long_q})
        self.assertEqual(len(out2["q"]), 200)
        self.assertEqual(run_feature({"deals": []})["q"], "")
        self.assertEqual(run_feature({"deals": [], "q": None})["q"], "")

    def test_stage_normalization(self):
        self.assertEqual(run_feature({"deals": []})["stage"], "all")
        self.assertEqual(run_feature({"deals": [], "stage": None})["stage"], "all")
        self.assertEqual(run_feature({"deals": [], "stage": ""})["stage"], "all")
        self.assertEqual(run_feature({"deals": [], "stage": "all"})["stage"], "all")
        self.assertEqual(run_feature({"deals": [], "stage": "  won  "})["stage"], "won")

    def test_extra_keys_ignored_and_inputs_preserved(self):
        payload = {
            "deals": [{"pk": 2, "title": "B", "stage": "new", "junk": 1}, {"pk": 1, "title": "A", "stage": "new"}],
            "q": "",
            "stage": "all",
            "page": 1,
            "extra": "ignore",
        }
        snapshot = copy.deepcopy(payload)
        out = run_feature(payload)
        self.assertEqual(payload, snapshot)
        self.assertEqual(out["total_count"], 2)

    def test_errors(self):
        with self.assertRaises(ValueError):
            run_feature(None)
        with self.assertRaises(ValueError):
            run_feature([])
        with self.assertRaises(ValueError):
            run_feature("x")
        with self.assertRaises(ValueError):
            run_feature({"deals": {}})
        with self.assertRaises(ValueError):
            run_feature({"deals": [None]})
        with self.assertRaises(ValueError):
            run_feature({"deals": [{"pk": True, "title": "A", "stage": "new"}]})
        with self.assertRaises(ValueError):
            run_feature({"deals": [{"pk": 0, "title": "A", "stage": "new"}]})
        with self.assertRaises(ValueError):
            run_feature({"deals": [{"pk": 1, "title": "A", "stage": "bad"}]})
        with self.assertRaises(ValueError):
            run_feature({"deals": [{"pk": 1, "title": "A", "stage": "new"}, {"pk": 1, "title": "B", "stage": "new"}]})
        with self.assertRaises(ValueError):
            run_feature({"deals": [{"pk": 1, "title": "x" * 181, "stage": "new"}]})
        with self.assertRaises(ValueError):
            run_feature({"deals": [], "q": 123})
        with self.assertRaises(ValueError):
            run_feature({"deals": [], "q": "x" * 5001})
        with self.assertRaises(ValueError):
            run_feature({"deals": [], "stage": 123})
        with self.assertRaises(ValueError):
            run_feature({"deals": [], "stage": "bad"})
        with self.assertRaises(ValueError):
            run_feature({"deals": [], "page": 1.5})
        with self.assertRaises(ValueError):
            run_feature({"deals": [], "page": True})
        with self.assertRaises(ValueError):
            run_feature({"deals": [], "page": []})

    def test_missing_title_or_pk_raises(self):
        with self.assertRaises(ValueError):
            run_feature({"deals": [{"title": "A", "stage": "new"}]})
        with self.assertRaises(ValueError):
            run_feature({"deals": [{"pk": 1, "stage": "new"}]})


if __name__ == "__main__":
    unittest.main()
