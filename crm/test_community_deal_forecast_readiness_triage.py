import copy
import unittest
from crm.features.deal_forecast_readiness_triage import run_feature


class DealForecastReadinessTriageTests(unittest.TestCase):
    def test_example_partition(self):
        payload = {
            "today": "2026-05-15",
            "deals": [
                {"pk": 1, "stage": "new", "expected_close": None, "title": "Padaria"},
                {"pk": 2, "stage": "proposal", "expected_close": "2026-05-10"},
                {"pk": 3, "stage": "qualified", "expected_close": "2026-05-15"},
                {"pk": 4, "stage": "proposal", "expected_close": "2026-05-20"},
                {"pk": 5, "stage": "won", "expected_close": "2026-05-01"},
            ],
        }
        result = run_feature(payload)
        self.assertEqual(result["deal_count"], 5)
        self.assertEqual(result["open_count"], 4)
        self.assertEqual(result["closed_count"], 1)
        self.assertEqual(result["missing_pks"], [1])
        self.assertEqual(result["overdue_pks"], [2])
        self.assertEqual(result["due_today_pks"], [3])
        self.assertEqual(result["upcoming_pks"], [4])
        self.assertEqual(result["missing_count"], 1)
        self.assertEqual(result["overdue_count"], 1)
        self.assertEqual(result["due_today_count"], 1)
        self.assertEqual(result["upcoming_count"], 1)

    def test_closed_only_never_bucketed(self):
        payload = {
            "today": "2026-01-10",
            "deals": [
                {"pk": 10, "stage": "lost", "expected_close": None},
                {"pk": 11, "stage": "won", "expected_close": "2025-12-01"},
            ],
        }
        result = run_feature(payload)
        self.assertEqual(result, {
            "deal_count": 2,
            "open_count": 0,
            "closed_count": 2,
            "missing_count": 0,
            "overdue_count": 0,
            "due_today_count": 0,
            "upcoming_count": 0,
            "missing_pks": [],
            "overdue_pks": [],
            "due_today_pks": [],
            "upcoming_pks": [],
        })

    def test_empty_leap_day(self):
        result = run_feature({"today": "2024-02-29", "deals": [], "extra": "ignored"})
        self.assertEqual(result["deal_count"], 0)
        self.assertEqual(result["open_count"], 0)
        self.assertEqual(result["closed_count"], 0)
        self.assertEqual(result["missing_pks"], [])

    def test_missing_deals_defaults_empty(self):
        result = run_feature({"today": "2026-05-15"})
        self.assertEqual(result["deal_count"], 0)
        self.assertEqual(result["open_count"], 0)

    def test_extra_keys_ignored(self):
        payload = {
            "today": "2026-05-15",
            "other": 123,
            "deals": [
                {"pk": 1, "stage": "new", "expected_close": None, "extra": "x", "title": "y"},
            ],
        }
        result = run_feature(payload)
        self.assertEqual(result["missing_pks"], [1])

    def test_sorted_buckets(self):
        payload = {
            "today": "2026-05-15",
            "deals": [
                {"pk": 30, "stage": "new", "expected_close": None},
                {"pk": 5, "stage": "new", "expected_close": None},
                {"pk": 20, "stage": "proposal", "expected_close": "2026-05-01"},
                {"pk": 7, "stage": "qualified", "expected_close": "2026-05-01"},
                {"pk": 9, "stage": "proposal", "expected_close": "2026-06-01"},
                {"pk": 8, "stage": "new", "expected_close": "2026-06-01"},
            ],
        }
        result = run_feature(payload)
        self.assertEqual(result["missing_pks"], [5, 30])
        self.assertEqual(result["overdue_pks"], [7, 20])
        self.assertEqual(result["upcoming_pks"], [8, 9])
        self.assertEqual(result["missing_count"], 2)
        self.assertEqual(result["overdue_count"], 2)
        self.assertEqual(result["upcoming_count"], 2)

    def test_closed_overdue_and_null_never_bucketed(self):
        payload = {
            "today": "2026-05-15",
            "deals": [
                {"pk": 1, "stage": "won", "expected_close": "2026-01-01"},
                {"pk": 2, "stage": "lost", "expected_close": None},
                {"pk": 3, "stage": "won", "expected_close": "2026-05-15"},
                {"pk": 4, "stage": "lost", "expected_close": "2026-12-31"},
            ],
        }
        result = run_feature(payload)
        self.assertEqual(result["closed_count"], 4)
        self.assertEqual(result["open_count"], 0)
        self.assertEqual(result["missing_pks"], [])
        self.assertEqual(result["overdue_pks"], [])
        self.assertEqual(result["due_today_pks"], [])
        self.assertEqual(result["upcoming_pks"], [])

    def test_rejects_non_dict_payload(self):
        for bad in [None, [], "x", 123, True]:
            with self.assertRaises(ValueError):
                run_feature(bad)

    def test_rejects_missing_and_bad_today(self):
        with self.assertRaises(ValueError):
            run_feature({"deals": []})
        for bad in [None, "", "2026-13-01", "2026-02-30", "2023-02-29", "15-05-2026", "2026/05/15", 123, True, "2026-5-5"]:
            with self.assertRaises(ValueError):
                run_feature({"today": bad, "deals": []})

    def test_rejects_feb_30_and_unknown_stage(self):
        with self.assertRaises(ValueError):
            run_feature({"today": "2026-02-30", "deals": []})
        with self.assertRaises(ValueError):
            run_feature({
                "today": "2026-05-15",
                "deals": [{"pk": 1, "stage": "archived", "expected_close": None}],
            })
        with self.assertRaises(ValueError):
            run_feature({
                "today": "2026-05-15",
                "deals": [{"pk": 1, "stage": "New", "expected_close": None}],
            })

    def test_rejects_bad_expected_close(self):
        for bad in ["", "2026-02-30", "not-a-date", 123, True, [], {}]:
            with self.assertRaises(ValueError):
                run_feature({
                    "today": "2026-05-15",
                    "deals": [{"pk": 1, "stage": "new", "expected_close": bad}],
                })
        with self.assertRaises(ValueError):
            run_feature({
                "today": "2026-05-15",
                "deals": [{"pk": 1, "stage": "new"}],
            })

    def test_rejects_bad_pk(self):
        for bad in [0, -1, 9007199254740992, True, False, "1", 1.5, None]:
            with self.assertRaises(ValueError):
                run_feature({
                    "today": "2026-05-15",
                    "deals": [{"pk": bad, "stage": "new", "expected_close": None}],
                })
        with self.assertRaises(ValueError):
            run_feature({
                "today": "2026-05-15",
                "deals": [{"stage": "new", "expected_close": None}],
            })

    def test_rejects_duplicates(self):
        with self.assertRaises(ValueError):
            run_feature({
                "today": "2026-05-15",
                "deals": [
                    {"pk": 1, "stage": "new", "expected_close": None},
                    {"pk": 1, "stage": "qualified", "expected_close": "2026-05-20"},
                ],
            })

    def test_rejects_bad_deals_container(self):
        with self.assertRaises(ValueError):
            run_feature({"today": "2026-05-15", "deals": None})
        with self.assertRaises(ValueError):
            run_feature({"today": "2026-05-15", "deals": "x"})
        with self.assertRaises(ValueError):
            run_feature({"today": "2026-05-15", "deals": ["x"]})
        with self.assertRaises(ValueError):
            run_feature({
                "today": "2026-05-15",
                "deals": [{"pk": 1, "stage": "new", "expected_close": None}] * 101,
            })

    def test_preserves_inputs(self):
        payload = {
            "today": "2026-05-15",
            "deals": [
                {"pk": 2, "stage": "proposal", "expected_close": "2026-05-10"},
                {"pk": 1, "stage": "new", "expected_close": None},
            ],
        }
        snapshot = copy.deepcopy(payload)
        run_feature(payload)
        self.assertEqual(payload, snapshot)

    def test_deterministic(self):
        payload = {
            "today": "2026-05-15",
            "deals": [{"pk": 1, "stage": "new", "expected_close": None}],
        }
        first = run_feature(payload)
        second = run_feature({"today": "2026-05-15", "deals": [{"pk": 1, "stage": "new", "expected_close": None}]})
        self.assertEqual(first, second)

    def test_leap_year_boundaries(self):
        ok = run_feature({
            "today": "2024-02-29",
            "deals": [{"pk": 1, "stage": "new", "expected_close": "2024-02-29"}],
        })
        self.assertEqual(ok["due_today_pks"], [1])
        with self.assertRaises(ValueError):
            run_feature({"today": "2023-02-29", "deals": []})
        with self.assertRaises(ValueError):
            run_feature({
                "today": "2026-05-15",
                "deals": [{"pk": 1, "stage": "new", "expected_close": "2023-02-29"}],
            })


if __name__ == "__main__":
    unittest.main()
