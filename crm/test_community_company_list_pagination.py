import copy
import unittest

from crm.features.company_list_pagination import run_feature


def _make(n, prefix="C"):
    out = []
    for i in range(n):
        out.append({"pk": i + 1, "name": prefix + str(1000 + i)})
    return out


class CompanyListPaginationTest(unittest.TestCase):
    def test_example_filter_padaria(self):
        payload = {"companies": [{"name": "Beta Mercado", "pk": 2}, {"name": "Alfa Padaria", "pk": 1}], "page": "1", "q": " padaria "}
        out = run_feature(payload)
        self.assertEqual(out, {"has_next": False, "has_previous": False, "next_page": None, "num_pages": 1, "page": 1, "per_page": 50, "prev_page": None, "q": "padaria", "results": [{"name": "Alfa Padaria", "pk": 1}], "total_count": 1})

    def test_example_ordering(self):
        payload = {"companies": [{"name": "Zeta", "pk": 3}, {"name": "Alfa", "pk": 1}, {"name": "alfa", "pk": 2}], "page": 99, "q": ""}
        out = run_feature(payload)
        self.assertEqual(out["q"], "")
        self.assertEqual(out["page"], 1)
        self.assertEqual(out["total_count"], 3)
        self.assertEqual(out["results"], [{"name": "Alfa", "pk": 1}, {"name": "alfa", "pk": 2}, {"name": "Zeta", "pk": 3}])

    def test_order_by_fold_then_name_then_pk(self):
        payload = {"companies": [{"name": "alfa", "pk": 2}, {"name": "Alfa", "pk": 1}, {"name": "ALFA", "pk": 5}, {"name": "Beta", "pk": 3}], "q": "", "page": 1}
        out = run_feature(payload)
        self.assertEqual([r["pk"] for r in out["results"]], [5, 1, 2, 3])

    def test_pk_tiebreak(self):
        payload = {"companies": [{"name": "Same", "pk": 9}, {"name": "Same", "pk": 4}], "q": "", "page": 1}
        out = run_feature(payload)
        self.assertEqual(out["results"], [{"pk": 4, "name": "Same"}, {"pk": 9, "name": "Same"}])

    def test_filter_casefold_substring(self):
        companies = [{"pk": 1, "name": "Alfa Padaria"}, {"pk": 2, "name": "BETA mercado"}, {"pk": 3, "name": "Gamma"}]
        out = run_feature({"companies": companies, "q": "ALFA", "page": 1})
        self.assertEqual(out["results"], [{"pk": 1, "name": "Alfa Padaria"}])
        out2 = run_feature({"companies": companies, "q": "beta MERC", "page": 1})
        self.assertEqual(out2["results"], [{"pk": 2, "name": "BETA mercado"}])

    def test_empty_q_keeps_all(self):
        companies = [{"pk": 2, "name": "B"}, {"pk": 1, "name": "A"}]
        for q in ["", None]:
            payload = {"companies": companies, "page": 1}
            if q is not None:
                payload["q"] = q
            out = run_feature(payload)
            self.assertEqual(out["total_count"], 2)
            self.assertEqual(out["q"], "")
        out_missing = run_feature({"companies": companies})
        self.assertEqual(out_missing["q"], "")
        self.assertEqual(out_missing["page"], 1)

    def test_q_strip_and_truncate(self):
        out = run_feature({"companies": [], "q": " \t\n\rhello \t\n\r", "page": 1})
        self.assertEqual(out["q"], "hello")
        long_q = "   " + "x" * 250 + "   "
        out2 = run_feature({"companies": [], "q": long_q, "page": 1})
        self.assertEqual(out2["q"], "x" * 200)

    def test_pagination_fifty_per_page(self):
        companies = _make(55)
        p1 = run_feature({"companies": companies, "q": "", "page": 1})
        self.assertEqual(p1["total_count"], 55)
        self.assertEqual(p1["num_pages"], 2)
        self.assertEqual(p1["per_page"], 50)
        self.assertEqual(len(p1["results"]), 50)
        self.assertFalse(p1["has_previous"])
        self.assertTrue(p1["has_next"])
        self.assertIsNone(p1["prev_page"])
        self.assertEqual(p1["next_page"], 2)
        p2 = run_feature({"companies": companies, "q": "", "page": 2})
        self.assertEqual(p2["page"], 2)
        self.assertEqual(len(p2["results"]), 5)
        self.assertTrue(p2["has_previous"])
        self.assertFalse(p2["has_next"])
        self.assertEqual(p2["prev_page"], 1)
        self.assertIsNone(p2["next_page"])

    def test_empty_is_page_one_of_one(self):
        out = run_feature({"companies": [], "q": "", "page": 1})
        self.assertEqual(out["total_count"], 0)
        self.assertEqual(out["num_pages"], 1)
        self.assertEqual(out["page"], 1)
        self.assertEqual(out["results"], [])
        self.assertFalse(out["has_previous"])
        self.assertFalse(out["has_next"])

    def test_non_integer_page_goes_first(self):
        companies = _make(100)
        for bad in ["abc", "12.5", "1_0", "+5", "-", "--3"]:
            out = run_feature({"companies": companies, "q": "", "page": bad})
            self.assertEqual(out["page"], 1, msg=bad)

    def test_out_of_range_page_goes_last(self):
        companies = _make(100)
        for pg, want in [(99, 2), (0, 2), (-5, 2), ("99", 2), ("0", 2), ("-3", 2), ("  2  ", 2)]:
            out = run_feature({"companies": companies, "q": "", "page": pg})
            self.assertEqual(out["page"], want, msg=repr(pg))
        empty = run_feature({"companies": [], "page": 99})
        self.assertEqual(empty["page"], 1)

    def test_page_empty_string_and_none_default(self):
        companies = _make(100)
        for pg in [None, "", "   \t\n\r  "]:
            payload = {"companies": companies, "q": ""}
            if pg is not None:
                payload["page"] = pg
            out = run_feature(payload)
            self.assertEqual(out["page"], 1)
        missing = run_feature({})
        self.assertEqual(missing["page"], 1)
        self.assertEqual(missing["q"], "")
        self.assertEqual(missing["total_count"], 0)

    def test_middle_page_flags(self):
        companies = _make(120)
        out = run_feature({"companies": companies, "page": 2, "q": ""})
        self.assertEqual(out["num_pages"], 3)
        self.assertTrue(out["has_previous"])
        self.assertTrue(out["has_next"])
        self.assertEqual(out["prev_page"], 1)
        self.assertEqual(out["next_page"], 3)

    def test_extra_keys_ignored_and_copies(self):
        payload = {"companies": [{"pk": 1, "name": "A", "extra": 9}], "q": "", "page": 1, "other": 123}
        out = run_feature(payload)
        self.assertEqual(out["results"], [{"pk": 1, "name": "A"}])
        self.assertEqual(set(out.keys()), {"q", "page", "per_page", "num_pages", "total_count", "results", "has_previous", "has_next", "prev_page", "next_page"})
        out["results"][0]["pk"] = 999
        out2 = run_feature(payload)
        self.assertEqual(out2["results"][0]["pk"], 1)

    def test_no_mutation(self):
        payload = {"companies": [{"pk": 2, "name": "Beta"}, {"pk": 1, "name": "Alfa"}], "q": " beta ", "page": "1"}
        before = copy.deepcopy(payload)
        run_feature(payload)
        self.assertEqual(payload, before)

    def test_validation_errors(self):
        with self.assertRaises(ValueError):
            run_feature(None)
        with self.assertRaises(ValueError):
            run_feature([])
        with self.assertRaises(ValueError):
            run_feature({"companies": {}, "q": "", "page": 1})
        with self.assertRaises(ValueError):
            run_feature({"companies": [{"pk": 1, "name": "A"}, {"pk": 1, "name": "B"}], "q": "", "page": 1})
        with self.assertRaises(ValueError):
            run_feature({"companies": [{"pk": True, "name": "A"}], "q": "", "page": 1})
        with self.assertRaises(ValueError):
            run_feature({"companies": [{"pk": 0, "name": "A"}], "q": "", "page": 1})
        with self.assertRaises(ValueError):
            run_feature({"companies": [{"pk": 9007199254740992, "name": "A"}], "q": "", "page": 1})
        with self.assertRaises(ValueError):
            run_feature({"companies": [{"pk": "1", "name": "A"}], "q": "", "page": 1})
        with self.assertRaises(ValueError):
            run_feature({"companies": [{"pk": 1, "name": "x" * 181}], "q": "", "page": 1})
        with self.assertRaises(ValueError):
            run_feature({"companies": [{"pk": 1}], "q": "", "page": 1})
        with self.assertRaises(ValueError):
            run_feature({"companies": ["nope"], "q": "", "page": 1})
        with self.assertRaises(ValueError):
            run_feature({"companies": [], "q": 123, "page": 1})
        with self.assertRaises(ValueError):
            run_feature({"companies": [], "q": "x" * 5001, "page": 1})
        with self.assertRaises(ValueError):
            run_feature({"companies": [], "q": "", "page": True})
        with self.assertRaises(ValueError):
            run_feature({"companies": [], "q": "", "page": 1.5})
        with self.assertRaises(ValueError):
            run_feature({"companies": [], "q": "", "page": [1]})
        with self.assertRaises(ValueError):
            run_feature({"companies": [{"pk": 1, "name": 5}], "q": "", "page": 1})

    def test_deterministic(self):
        payload = {"companies": [{"pk": 2, "name": "Beta"}, {"pk": 1, "name": "Alfa"}], "q": "", "page": 1}
        self.assertEqual(run_feature(payload), run_feature(copy.deepcopy(payload)))


if __name__ == "__main__":
    unittest.main()
