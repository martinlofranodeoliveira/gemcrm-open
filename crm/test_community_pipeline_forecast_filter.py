import copy
import unittest

from crm.features.pipeline_forecast_filter import run_feature


class PipelineForecastFilterTest(unittest.TestCase):
    def test_no_bounds_keeps_null_and_totals(self):
        payload = {
            "deals": [
                {"pk": 1, "title": "Padaria", "stage": "new", "value": "100.00", "expected_close": None},
                {"pk": 2, "title": "Mercado", "stage": "won", "value": "234.50", "expected_close": "2026-03-10"},
            ]
        }
        out = run_feature(payload)
        self.assertIsNone(out["start"])
        self.assertIsNone(out["end"])
        self.assertEqual(out["total_count"], 2)
        self.assertEqual(len(out["results"]), 2)
        self.assertIsNone(out["results"][0]["expected_close"])
        self.assertEqual(out["results"][0]["value_cents"], 10000)
        self.assertEqual(out["results"][0]["value_csv"], "100.00")
        self.assertEqual(out["results"][0]["value_display"], "R$ 100,00")
        self.assertEqual(out["results"][1]["value_cents"], 23450)
        self.assertEqual(out["by_stage"]["new"]["count"], 1)
        self.assertEqual(out["by_stage"]["new"]["total_cents"], 10000)
        self.assertEqual(out["by_stage"]["new"]["total_csv"], "100.00")
        self.assertEqual(out["by_stage"]["new"]["total_display"], "R$ 100,00")
        self.assertEqual(out["by_stage"]["won"]["total_cents"], 23450)
        self.assertEqual(out["grand"]["count"], 2)
        self.assertEqual(out["grand"]["total_cents"], 33450)
        self.assertEqual(out["grand"]["total_csv"], "334.50")
        self.assertEqual(out["grand"]["total_display"], "R$ 334,50")
        self.assertEqual(out["by_stage"]["lost"]["total_csv"], "0.00")
        self.assertEqual(out["by_stage"]["lost"]["total_display"], "R$ 0,00")

    def test_both_bounds_filter_null_out(self):
        payload = {
            "deals": [
                {"pk": 1, "title": "Padaria", "stage": "new", "value": "100.00", "expected_close": None},
                {"pk": 2, "title": "Mercado", "stage": "won", "value": "234.50", "expected_close": "2026-03-10"},
            ],
            "start": "2026-03-01",
            "end": "2026-03-31",
        }
        out = run_feature(payload)
        self.assertEqual(out["start"], "2026-03-01")
        self.assertEqual(out["end"], "2026-03-31")
        self.assertEqual(out["total_count"], 1)
        self.assertEqual(out["results"][0]["pk"], 2)
        self.assertEqual(out["grand"]["total_cents"], 23450)

    def test_single_start_bound_inclusive(self):
        payload = {
            "deals": [
                {"pk": 3, "title": "Oficina", "stage": "proposal", "value": "100.5", "expected_close": "2026-03-01"},
                {"pk": 4, "title": "Cafe", "stage": "proposal", "value": "20.05", "expected_close": "2026-02-28"},
                {"pk": 5, "title": "Null", "stage": "proposal", "value": "10.00", "expected_close": None},
            ],
            "start": "2026-03-01",
        }
        out = run_feature(payload)
        self.assertEqual(out["total_count"], 1)
        self.assertEqual(out["results"][0]["pk"], 3)
        self.assertEqual(out["results"][0]["value_cents"], 10050)
        self.assertEqual(out["results"][0]["value_csv"], "100.50")
        self.assertEqual(out["results"][0]["value_display"], "R$ 100,50")
        self.assertIsNone(out["end"])

    def test_single_end_bound_inclusive(self):
        payload = {
            "deals": [
                {"pk": 1, "title": "A", "stage": "new", "value": "10.00", "expected_close": "2026-03-31"},
                {"pk": 2, "title": "B", "stage": "new", "value": "10.00", "expected_close": "2026-04-01"},
                {"pk": 3, "title": "C", "stage": "new", "value": "10.00", "expected_close": None},
            ],
            "end": "2026-03-31",
        }
        out = run_feature(payload)
        self.assertEqual(out["total_count"], 1)
        self.assertEqual(out["results"][0]["pk"], 1)
        self.assertIsNone(out["start"])

    def test_empty_string_bounds_are_unbounded(self):
        payload = {
            "deals": [
                {"pk": 1, "title": "A", "stage": "lost", "value": "0.00", "expected_close": None},
            ],
            "start": "",
            "end": "",
        }
        out = run_feature(payload)
        self.assertIsNone(out["start"])
        self.assertIsNone(out["end"])
        self.assertEqual(out["total_count"], 1)

    def test_invalid_start_format_raises(self):
        with self.assertRaises(ValueError):
            run_feature({"deals": [], "start": "2026/03/01"})
        with self.assertRaises(ValueError):
            run_feature({"deals": [], "start": "2026-3-1"})
        with self.assertRaises(ValueError):
            run_feature({"deals": [], "end": 20260301})

    def test_impossible_calendar_date_raises(self):
        with self.assertRaises(ValueError):
            run_feature({"deals": [], "start": "2026-02-30"})
        with self.assertRaises(ValueError):
            run_feature({"deals": [], "end": "2026-13-01"})
        with self.assertRaises(ValueError):
            run_feature({
                "deals": [
                    {"pk": 1, "title": "A", "stage": "new", "value": "10.00", "expected_close": "2023-02-29"},
                ]
            })

    def test_start_after_end_raises(self):
        with self.assertRaises(ValueError):
            run_feature({"deals": [], "start": "2026-04-01", "end": "2026-03-01"})

    def test_invalid_stage_raises(self):
        with self.assertRaises(ValueError):
            run_feature({"deals": [{"pk": 1, "title": "A", "stage": "closing", "value": "10.00", "expected_close": None}]})

    def test_invalid_value_shapes_raise(self):
        for bad in ["01", "-10", "10.123", "abc", "", "10,00", " 10", 10, None]:
            with self.assertRaises(ValueError):
                run_feature({"deals": [{"pk": 1, "title": "A", "stage": "new", "value": bad, "expected_close": None}]})

    def test_value_exceeding_max_raises(self):
        with self.assertRaises(ValueError):
            run_feature({"deals": [{"pk": 1, "title": "A", "stage": "new", "value": "1000000000000.00", "expected_close": None}]})

    def test_bad_expected_close_raises(self):
        with self.assertRaises(ValueError):
            run_feature({"deals": [{"pk": 1, "title": "A", "stage": "new", "value": "10.00", "expected_close": "tomorrow"}]})
        with self.assertRaises(ValueError):
            run_feature({"deals": [{"pk": 1, "title": "A", "stage": "new", "value": "10.00", "expected_close": 123}]})

    def test_pk_bool_and_title_type_rejected(self):
        with self.assertRaises(ValueError):
            run_feature({"deals": [{"pk": True, "title": "A", "stage": "new", "value": "10.00", "expected_close": None}]})
        with self.assertRaises(ValueError):
            run_feature({"deals": [{"pk": 1, "title": 123, "stage": "new", "value": "10.00", "expected_close": None}]})
        with self.assertRaises(ValueError):
            run_feature({"deals": "not-a-list"})
        with self.assertRaises(ValueError):
            run_feature("not-an-object")

    def test_too_many_deals_raises(self):
        deals = [{"pk": i, "title": "T", "stage": "new", "value": "1.00", "expected_close": None} for i in range(5001)]
        with self.assertRaises(ValueError):
            run_feature({"deals": deals})

    def test_inputs_not_mutated(self):
        payload = {
            "deals": [
                {"pk": 1, "title": "A", "stage": "new", "value": "100.00", "expected_close": None, "extra": "keep"},
                {"pk": 2, "title": "B", "stage": "won", "value": "234.50", "expected_close": "2026-03-10"},
            ],
            "start": "2026-03-01",
            "end": "2026-03-31",
        }
        snapshot = copy.deepcopy(payload)
        run_feature(payload)
        self.assertEqual(payload, snapshot)

    def test_cents_math_without_float_and_no_separator(self):
        out = run_feature({"deals": [{"pk": 1, "title": "Big", "stage": "qualified", "value": "1234567.80", "expected_close": None}]})
        self.assertEqual(out["results"][0]["value_cents"], 123456780)
        self.assertEqual(out["results"][0]["value_csv"], "1234567.80")
        self.assertEqual(out["results"][0]["value_display"], "R$ 1234567,80")
        self.assertNotIn(",", out["results"][0]["value_csv"])
        self.assertNotIn(".", out["results"][0]["value_display"].split(" ")[1].split(",")[0])
        out2 = run_feature({"deals": [{"pk": 1, "title": "A", "stage": "new", "value": "100", "expected_close": None}]})
        self.assertEqual(out2["results"][0]["value_cents"], 10000)
        self.assertEqual(out2["results"][0]["value_csv"], "100.00")

    def test_missing_keys_defaults_and_extra_ignored(self):
        out = run_feature({})
        self.assertEqual(out["total_count"], 0)
        self.assertEqual(out["grand"]["count"], 0)
        self.assertEqual(out["grand"]["total_csv"], "0.00")
        self.assertEqual(out["grand"]["total_display"], "R$ 0,00")
        out2 = run_feature({
            "deals": [{"pk": 1, "title": "A", "stage": "new", "value": "5.00", "owner": 99}],
            "unknown": 1,
        })
        self.assertEqual(out2["total_count"], 1)


if __name__ == "__main__":
    unittest.main()
