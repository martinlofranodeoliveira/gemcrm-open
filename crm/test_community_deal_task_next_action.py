import copy
import unittest

from crm.features.deal_task_next_action import run_feature


class DealTaskNextActionTest(unittest.TestCase):
    def test_contract_example_basic(self):
        payload = {
            "deals": [{"pk": 1, "title": "Padaria"}, {"pk": 2, "title": "Mercado"}],
            "tasks": [
                {"completed": False, "deal": 1, "due_date": "2026-03-10", "pk": 10, "title": "Ligar"},
                {"completed": False, "deal": 1, "due_date": "2026-03-08", "pk": 11, "title": "Visita"},
                {"completed": True, "deal": 2, "due_date": "2026-03-09", "pk": 12, "title": "Proposta"},
            ],
        }
        out = run_feature(payload)
        self.assertEqual(out["total_deals"], 2)
        self.assertEqual(out["deals_with_open"], 1)
        self.assertEqual(out["deals_without_open"], 1)
        self.assertEqual(out["total_open_tasks"], 2)
        self.assertEqual(len(out["results"]), 2)
        first = out["results"][0]
        self.assertEqual(first["deal_pk"], 1)
        self.assertEqual(first["deal_title"], "Padaria")
        self.assertTrue(first["has_open"])
        self.assertEqual(first["open_count"], 2)
        self.assertEqual(first["next_pk"], 11)
        self.assertEqual(first["next_title"], "Visita")
        self.assertEqual(first["next_due_date"], "2026-03-08")
        second = out["results"][1]
        self.assertEqual(second["deal_pk"], 2)
        self.assertFalse(second["has_open"])
        self.assertEqual(second["open_count"], 0)
        self.assertIsNone(second["next_pk"])
        self.assertIsNone(second["next_title"])
        self.assertIsNone(second["next_due_date"])

    def test_empty_coverage(self):
        out = run_feature({"deals": [{"pk": 5, "title": "Oficina"}], "tasks": []})
        self.assertEqual(out["total_deals"], 1)
        self.assertEqual(out["deals_with_open"], 0)
        self.assertEqual(out["deals_without_open"], 1)
        self.assertEqual(out["total_open_tasks"], 0)
        self.assertEqual(len(out["results"]), 1)
        row = out["results"][0]
        self.assertEqual(row["deal_pk"], 5)
        self.assertEqual(row["deal_title"], "Oficina")
        self.assertFalse(row["has_open"])
        self.assertEqual(row["open_count"], 0)
        self.assertIsNone(row["next_pk"])
        self.assertIsNone(row["next_title"])
        self.assertIsNone(row["next_due_date"])

    def test_earliest_wins_tie_and_trim(self):
        payload = {
            "deals": [{"pk": 1, "title": "A"}, {"pk": 2, "title": "B"}],
            "tasks": [
                {"completed": False, "deal": 1, "due_date": "2026-04-01", "pk": 20, "title": "Z "},
                {"completed": False, "deal": 1, "due_date": "2026-04-01", "pk": 19, "title": " Y "},
                {"completed": False, "deal": None, "due_date": "2026-04-02", "pk": 21, "title": "Livre"},
                {"completed": False, "deal": 99, "due_date": "2026-04-03", "pk": 22, "title": "Fantasma"},
                {"completed": True, "deal": 2, "due_date": "2026-04-05", "pk": 23, "title": "Fechada"},
            ],
        }
        out = run_feature(payload)
        self.assertEqual(out["total_deals"], 2)
        self.assertEqual(out["deals_with_open"], 1)
        self.assertEqual(out["deals_without_open"], 1)
        self.assertEqual(out["total_open_tasks"], 4)
        first = out["results"][0]
        self.assertTrue(first["has_open"])
        self.assertEqual(first["open_count"], 2)
        self.assertEqual(first["next_pk"], 19)
        self.assertEqual(first["next_title"], "Y")
        self.assertEqual(first["next_due_date"], "2026-04-01")
        second = out["results"][1]
        self.assertFalse(second["has_open"])
        self.assertEqual(second["open_count"], 0)
        self.assertIsNone(second["next_pk"])

    def test_completed_never_counts(self):
        payload = {
            "deals": [{"pk": 1, "title": "Solo"}],
            "tasks": [
                {"completed": True, "deal": 1, "due_date": "2026-01-01", "pk": 1, "title": "Done"},
                {"completed": False, "deal": 1, "due_date": "2026-02-01", "pk": 2, "title": "Open"},
            ],
        }
        out = run_feature(payload)
        self.assertEqual(out["total_open_tasks"], 1)
        row = out["results"][0]
        self.assertEqual(row["open_count"], 1)
        self.assertEqual(row["next_pk"], 2)

    def test_null_and_unknown_only_total(self):
        payload = {
            "deals": [{"pk": 1, "title": "A"}],
            "tasks": [
                {"completed": False, "due_date": "2026-05-01", "pk": 30, "title": "NoDeal", "deal": None},
                {"completed": False, "due_date": "2026-05-02", "pk": 31, "title": "Missing"},
                {"completed": False, "due_date": "2026-05-03", "pk": 32, "title": "Ghost", "deal": 999},
            ],
        }
        out = run_feature(payload)
        self.assertEqual(out["total_open_tasks"], 3)
        row = out["results"][0]
        self.assertEqual(row["open_count"], 0)
        self.assertFalse(row["has_open"])
        self.assertIsNone(row["next_pk"])

    def test_malformed_raises(self):
        bad_payloads = [
            None,
            [],
            "x",
            {"deals": {}, "tasks": []},
            {"deals": [], "tasks": {}},
            {"deals": [{"pk": True, "title": "A"}], "tasks": []},
            {"deals": [{"pk": 0, "title": "A"}], "tasks": []},
            {"deals": [{"pk": 1, "title": "   \t\n\r  "}], "tasks": []},
            {"deals": [{"pk": 1, "title": "A"}, {"pk": 1, "title": "B"}], "tasks": []},
            {"deals": [], "tasks": [{"pk": 1, "title": "T", "due_date": "2026-01-01", "completed": False, "deal": True}]},
            {"deals": [], "tasks": [{"pk": 1, "title": "T", "due_date": "2026-13-01", "completed": False}]},
            {"deals": [], "tasks": [{"pk": 1, "title": "T", "due_date": "2023-02-29", "completed": False}]},
            {"deals": [], "tasks": [{"pk": 1, "title": "T", "due_date": "2026-01-01", "completed": 0}]},
            {"deals": [], "tasks": [
                {"pk": 1, "title": "A", "due_date": "2026-01-01", "completed": False},
                {"pk": 1, "title": "B", "due_date": "2026-01-02", "completed": False},
            ]},
            {"deals": [{"pk": 1, "title": "x" * 181}], "tasks": []},
            {"deals": [], "tasks": [{"pk": 1, "title": "", "due_date": "2026-01-01", "completed": False}]},
            {"deals": [], "tasks": [{"pk": 1, "title": "T", "due_date": "2026-00-10", "completed": False}]},
            {"deals": [], "tasks": [{"pk": 1, "title": "T", "due_date": "0000-01-01", "completed": False}]},
            {"deals": [], "tasks": [{"pk": 1, "title": "T", "due_date": "2026-04-31", "completed": False}]},
        ]
        for bad in bad_payloads:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    run_feature(bad)

    def test_leap_year_accepts_2024_feb29(self):
        payload = {
            "deals": [{"pk": 1, "title": "L"}],
            "tasks": [{"pk": 7, "title": "Leap", "due_date": "2024-02-29", "completed": False, "deal": 1}],
        }
        out = run_feature(payload)
        self.assertEqual(out["total_open_tasks"], 1)
        self.assertEqual(out["results"][0]["next_due_date"], "2024-02-29")

    def test_repeated_equal_and_no_mutation(self):
        payload = {
            "deals": [{"pk": 2, "title": "  B  "}, {"pk": 1, "title": "A"}],
            "tasks": [
                {"pk": 5, "title": " T ", "due_date": "2026-06-02", "completed": False, "deal": 1},
                {"pk": 4, "title": "S", "due_date": "2026-06-01", "completed": False, "deal": 1, "extra": 1},
            ],
            "extra_root": 99,
        }
        snapshot = copy.deepcopy(payload)
        first = run_feature(payload)
        second = run_feature(payload)
        self.assertEqual(first, second)
        self.assertEqual(payload, snapshot)
        self.assertEqual(first["results"][0]["deal_pk"], 2)
        self.assertEqual(first["results"][1]["next_pk"], 4)


if __name__ == "__main__":
    unittest.main()
