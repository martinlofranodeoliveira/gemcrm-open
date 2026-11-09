import copy
import unittest

from crm.features.task_workload_summary import run_feature


class TaskWorkloadSummaryTests(unittest.TestCase):
    def test_mixed_buckets_example(self):
        payload = {
            "today": "2026-05-12",
            "tasks": [
                {"pk": 1, "title": "Ligar", "due_date": "2026-05-10", "completed": False},
                {"pk": 2, "title": "Visita", "due_date": "2026-05-12", "completed": False},
                {"pk": 3, "title": "Proposta", "due_date": "2026-05-15", "completed": False},
                {"pk": 4, "title": "Feito", "due_date": "2026-05-09", "completed": True},
            ],
        }
        expected = {
            "today": "2026-05-12",
            "task_count": 4,
            "open_count": 3,
            "overdue_count": 1,
            "today_count": 1,
            "upcoming_count": 1,
            "completed_count": 1,
            "overdue_pks": [1],
            "today_pks": [2],
            "upcoming_pks": [3],
            "completed_pks": [4],
        }
        self.assertEqual(run_feature(payload), expected)

    def test_empty_tasks(self):
        result = run_feature({"today": "2026-01-01", "tasks": []})
        self.assertEqual(result, {
            "today": "2026-01-01",
            "task_count": 0,
            "open_count": 0,
            "overdue_count": 0,
            "today_count": 0,
            "upcoming_count": 0,
            "completed_count": 0,
            "overdue_pks": [],
            "today_pks": [],
            "upcoming_pks": [],
            "completed_pks": [],
        })

    def test_missing_tasks_defaults_to_empty(self):
        result = run_feature({"today": "2026-01-01"})
        self.assertEqual(result["task_count"], 0)
        self.assertEqual(result["overdue_pks"], [])

    def test_overdue_sorted_by_date_then_pk(self):
        payload = {
            "today": "2026-05-12",
            "tasks": [
                {"pk": 10, "title": "B", "due_date": "2026-05-11", "completed": False},
                {"pk": 5, "title": "A", "due_date": "2026-05-10", "completed": False},
                {"pk": 7, "title": "C", "due_date": "2026-05-10", "completed": False},
            ],
        }
        result = run_feature(payload)
        self.assertEqual(result["overdue_pks"], [5, 7, 10])
        self.assertEqual(result["overdue_count"], 3)
        self.assertEqual(result["open_count"], 3)

    def test_completed_ignores_date(self):
        payload = {
            "today": "2026-05-12",
            "tasks": [
                {"pk": 1, "title": "A", "due_date": "2026-01-01", "completed": True},
                {"pk": 2, "title": "B", "due_date": "2026-05-12", "completed": True},
                {"pk": 3, "title": "C", "due_date": "2030-12-31", "completed": True},
                {"pk": 4, "title": "D", "due_date": "2026-05-12", "completed": False},
            ],
        }
        result = run_feature(payload)
        self.assertEqual(result["completed_pks"], [1, 2, 3])
        self.assertEqual(result["today_pks"], [4])
        self.assertEqual(result["overdue_pks"], [])
        self.assertEqual(result["upcoming_pks"], [])

    def test_counts_match_lengths(self):
        payload = {
            "today": "2026-05-12",
            "tasks": [
                {"pk": 1, "title": "A", "due_date": "2026-05-10", "completed": False},
                {"pk": 2, "title": "B", "due_date": "2026-05-12", "completed": False},
                {"pk": 3, "title": "C", "due_date": "2026-05-13", "completed": False},
                {"pk": 4, "title": "D", "due_date": "2026-05-10", "completed": True},
            ],
        }
        result = run_feature(payload)
        self.assertEqual(result["overdue_count"], len(result["overdue_pks"]))
        self.assertEqual(result["today_count"], len(result["today_pks"]))
        self.assertEqual(result["upcoming_count"], len(result["upcoming_pks"]))
        self.assertEqual(result["completed_count"], len(result["completed_pks"]))
        self.assertEqual(result["open_count"], result["overdue_count"] + result["today_count"] + result["upcoming_count"])
        self.assertEqual(result["task_count"], result["open_count"] + result["completed_count"])

    def test_invalid_today_values(self):
        bad_todays = ["2026-02-30", "2023-02-29", "2026-13-01", "2026-00-10", "2026-05-32", "not-a-date", "2026/05/12", "", 123, None]
        for bad in bad_todays:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    run_feature({"today": bad, "tasks": []})
        with self.assertRaises(ValueError):
            run_feature({"tasks": []})
        with self.assertRaises(ValueError):
            run_feature(None)
        with self.assertRaises(ValueError):
            run_feature([])

    def test_invalid_due_dates(self):
        for bad_date in ["2026-02-30", "2023-02-29", "2026-13-01", "bad"]:
            with self.subTest(bad_date=bad_date):
                payload = {"today": "2026-05-12", "tasks": [{"pk": 1, "title": "A", "due_date": bad_date, "completed": False}]}
                with self.assertRaises(ValueError):
                    run_feature(payload)

    def test_leap_feb29_valid(self):
        result = run_feature({"today": "2024-02-29", "tasks": [{"pk": 1, "title": "A", "due_date": "2024-02-29", "completed": False}]})
        self.assertEqual(result["today_pks"], [1])
        with self.assertRaises(ValueError):
            run_feature({"today": "2023-02-29", "tasks": []})

    def test_non_bool_completed_rejected(self):
        for bad in [0, 1, "false", "true", None]:
            with self.subTest(bad=bad):
                payload = {"today": "2026-05-12", "tasks": [{"pk": 1, "title": "A", "due_date": "2026-05-12", "completed": bad}]}
                with self.assertRaises(ValueError):
                    run_feature(payload)

    def test_duplicate_pk_rejected(self):
        payload = {
            "today": "2026-05-12",
            "tasks": [
                {"pk": 1, "title": "A", "due_date": "2026-05-12", "completed": False},
                {"pk": 1, "title": "B", "due_date": "2026-05-13", "completed": False},
            ],
        }
        with self.assertRaises(ValueError):
            run_feature(payload)

    def test_too_many_tasks_rejected(self):
        tasks = []
        for i in range(201):
            tasks.append({"pk": i + 1, "title": "T", "due_date": "2026-05-12", "completed": False})
        with self.assertRaises(ValueError):
            run_feature({"today": "2026-05-12", "tasks": tasks})
        with self.assertRaises(ValueError):
            run_feature({"today": "2026-05-12", "tasks": None})
        with self.assertRaises(ValueError):
            run_feature({"today": "2026-05-12", "tasks": "nope"})

    def test_bool_pk_and_bounds_rejected(self):
        for bad_pk in [True, False, 0, 9007199254740992, "1", None]:
            with self.subTest(bad_pk=bad_pk):
                payload = {"today": "2026-05-12", "tasks": [{"pk": bad_pk, "title": "A", "due_date": "2026-05-12", "completed": False}]}
                with self.assertRaises(ValueError):
                    run_feature(payload)

    def test_title_bounds(self):
        with self.assertRaises(ValueError):
            run_feature({"today": "2026-05-12", "tasks": [{"pk": 1, "title": "", "due_date": "2026-05-12", "completed": False}]})
        with self.assertRaises(ValueError):
            run_feature({"today": "2026-05-12", "tasks": [{"pk": 1, "title": "x" * 181, "due_date": "2026-05-12", "completed": False}]})

    def test_extra_keys_ignored(self):
        payload = {
            "today": "2026-05-12",
            "extra": 999,
            "tasks": [{"pk": 1, "title": "A", "due_date": "2026-05-12", "completed": False, "extra_task": 1}],
        }
        result = run_feature(payload)
        self.assertEqual(result["today_pks"], [1])

    def test_inputs_not_mutated(self):
        payload = {
            "today": "2026-05-12",
            "tasks": [
                {"pk": 2, "title": "B", "due_date": "2026-05-10", "completed": False},
                {"pk": 1, "title": "A", "due_date": "2026-05-10", "completed": False},
            ],
        }
        snapshot = copy.deepcopy(payload)
        result = run_feature(payload)
        self.assertEqual(payload, snapshot)
        self.assertEqual(result["overdue_pks"], [1, 2])
        bad = {
            "today": "2026-05-12",
            "tasks": [
                {"pk": 1, "title": "A", "due_date": "2026-05-12", "completed": False},
                {"pk": 1, "title": "B", "due_date": "2026-05-12", "completed": False},
            ],
        }
        bad_snapshot = copy.deepcopy(bad)
        with self.assertRaises(ValueError):
            run_feature(bad)
        self.assertEqual(bad, bad_snapshot)


if __name__ == "__main__":
    unittest.main()
