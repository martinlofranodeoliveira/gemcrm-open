import copy
import unittest

from crm.features.task_date_filter import run_feature


def _task(pk, title, due_date, completed, extra=None):
    base = {"pk": pk, "title": title, "due_date": due_date, "completed": completed}
    if extra is not None:
        for k in extra:
            base[k] = extra[k]
    return base


class TaskDateFilterCommunityTest(unittest.TestCase):
    def test_today_example(self):
        payload = {
            "tasks": [
                _task(1, "Retorno Marina", "2026-03-09", False),
                _task(2, "Retorno Joao", "2026-03-10", False),
                _task(3, "Proposta final", "2026-03-11", False),
                _task(4, "Fechado", "2026-03-10", True),
            ],
            "today": "2026-03-10",
            "status": "today",
            "q": "",
        }
        out = run_feature(payload)
        self.assertEqual(out["today"], "2026-03-10")
        self.assertEqual(out["status_effective"], "today")
        self.assertEqual(out["q"], "")
        self.assertEqual(out["total_count"], 4)
        self.assertEqual(out["filtered_count"], 1)
        self.assertEqual(out["results"], [_task(2, "Retorno Joao", "2026-03-10", False)])

    def test_unknown_status_falls_back_to_all_with_q(self):
        payload = {
            "tasks": [
                _task(5, "Retorno Marina", "2026-03-09", False),
                _task(6, "Ligar fornecedor", "2026-03-09", False),
                _task(7, "RETORNO urgente", "2026-03-12", False),
            ],
            "today": "2026-03-10",
            "status": "weird",
            "q": "  retorno ",
        }
        out = run_feature(payload)
        self.assertEqual(out["status_effective"], "all")
        self.assertEqual(out["q"], "retorno")
        self.assertEqual(out["filtered_count"], 2)
        self.assertEqual([r["pk"] for r in out["results"]], [5, 7])

    def test_overdue_excludes_completed(self):
        payload = {
            "tasks": [
                _task(1, "Atrasada aberta", "2026-01-01", False),
                _task(2, "Atrasada fechada", "2026-01-01", True),
                _task(3, "Hoje aberta", "2026-03-10", False),
            ],
            "today": "2026-03-10",
            "status": "overdue",
            "q": "",
        }
        out = run_feature(payload)
        self.assertEqual(out["status_effective"], "overdue")
        self.assertEqual(out["filtered_count"], 1)
        self.assertEqual(out["results"][0]["pk"], 1)

    def test_open_completed_all(self):
        tasks = [
            _task(1, "Alpha", "2026-03-10", False),
            _task(2, "Beta", "2026-03-10", True),
        ]
        self.assertEqual([r["pk"] for r in run_feature({"tasks": tasks, "today": "2026-03-10", "status": "open", "q": ""})["results"]], [1])
        self.assertEqual([r["pk"] for r in run_feature({"tasks": tasks, "today": "2026-03-10", "status": "completed", "q": ""})["results"]], [2])
        self.assertEqual(run_feature({"tasks": tasks, "today": "2026-03-10", "status": "all", "q": ""})["filtered_count"], 2)

    def test_missing_empty_unknown_status_normalize_to_all(self):
        tasks = [_task(1, "Alpha", "2026-03-10", False)]
        self.assertEqual(run_feature({"tasks": tasks, "today": "2026-03-10"})["status_effective"], "all")
        self.assertEqual(run_feature({"tasks": tasks, "today": "2026-03-10", "status": None})["status_effective"], "all")
        self.assertEqual(run_feature({"tasks": tasks, "today": "2026-03-10", "status": ""})["status_effective"], "all")
        self.assertEqual(run_feature({"tasks": tasks, "today": "2026-03-10", "status": "OPEN"})["status_effective"], "all")
        self.assertEqual(run_feature({"tasks": tasks, "today": "2026-03-10", "status": "bogus"})["filtered_count"], 1)

    def test_upcoming_and_today_boundaries(self):
        tasks = [
            _task(1, "Past", "2026-03-09", False),
            _task(2, "Present", "2026-03-10", False),
            _task(3, "Future", "2026-03-11", False),
            _task(4, "Future done", "2026-03-11", True),
        ]
        up = run_feature({"tasks": tasks, "today": "2026-03-10", "status": "upcoming", "q": ""})
        self.assertEqual([r["pk"] for r in up["results"]], [3])
        td = run_feature({"tasks": tasks, "today": "2026-03-10", "status": "today", "q": ""})
        self.assertEqual([r["pk"] for r in td["results"]], [2])
        od = run_feature({"tasks": tasks, "today": "2026-03-10", "status": "overdue", "q": ""})
        self.assertEqual([r["pk"] for r in od["results"]], [1])

    def test_q_casefold_combines_with_every_status(self):
        tasks = [
            _task(1, "RETORNO Marina", "2026-03-09", False),
            _task(2, "retorno Joao", "2026-03-11", False),
            _task(3, "Other", "2026-03-09", False),
        ]
        for status in ("all", "open", "overdue", "upcoming"):
            out = run_feature({"tasks": tasks, "today": "2026-03-10", "status": status, "q": "  ReToRnO  "})
            self.assertEqual(out["q"], "ReToRnO")
            for row in out["results"]:
                self.assertIn("retorno", row["title"].casefold())
        empty_q = run_feature({"tasks": tasks, "today": "2026-03-10", "status": "overdue", "q": "   "})
        self.assertEqual(empty_q["q"], "")
        self.assertEqual(empty_q["filtered_count"], 2)

    def test_q_truncated_to_200_after_strip(self):
        long_q = "   " + ("x" * 250) + "   "
        out = run_feature({"tasks": [], "today": "2026-03-10", "status": "all", "q": long_q})
        self.assertEqual(out["q"], "x" * 200)
        none_q = run_feature({"tasks": [], "today": "2026-03-10", "status": "all", "q": None})
        self.assertEqual(none_q["q"], "")

    def test_sort_completed_due_date_pk_and_projection(self):
        tasks = [
            _task(9, "C", "2026-03-09", True, extra={"owner": "a", "notes": "x"}),
            _task(2, "B", "2026-03-09", False),
            _task(1, "A", "2026-03-09", False),
            _task(3, "D", "2026-03-08", False),
        ]
        out = run_feature({"tasks": tasks, "today": "2026-03-10", "status": "all", "q": "", "extra_top": 1})
        self.assertEqual([r["pk"] for r in out["results"]], [3, 1, 2, 9])
        for row in out["results"]:
            self.assertEqual(sorted(row.keys()), ["completed", "due_date", "pk", "title"])
        self.assertEqual(out["total_count"], 4)
        self.assertEqual(out["filtered_count"], 4)

    def test_invalid_payload_and_limits(self):
        with self.assertRaises(ValueError):
            run_feature([])
        with self.assertRaises(ValueError):
            run_feature({"tasks": {}, "today": "2026-03-10"})
        with self.assertRaises(ValueError):
            run_feature({"tasks": ["x"], "today": "2026-03-10"})
        big = [_task(i + 1, "T", "2026-03-10", False) for i in range(5001)]
        with self.assertRaises(ValueError):
            run_feature({"tasks": big, "today": "2026-03-10"})
        with self.assertRaises(ValueError):
            run_feature({"tasks": [], "today": "2026-03-10", "status": 1})
        with self.assertRaises(ValueError):
            run_feature({"tasks": [], "today": "2026-03-10", "q": 5})
        with self.assertRaises(ValueError):
            run_feature({"tasks": []})

    def test_malformed_tasks_rejected(self):
        with self.assertRaises(ValueError):
            run_feature({"tasks": [_task(True, "T", "2026-03-10", False)], "today": "2026-03-10"})
        with self.assertRaises(ValueError):
            run_feature({"tasks": [_task(0, "T", "2026-03-10", False)], "today": "2026-03-10"})
        with self.assertRaises(ValueError):
            run_feature({"tasks": [_task(9007199254740992, "T", "2026-03-10", False)], "today": "2026-03-10"})
        with self.assertRaises(ValueError):
            run_feature({"tasks": [_task(1, "", "2026-03-10", False)], "today": "2026-03-10"})
        with self.assertRaises(ValueError):
            run_feature({"tasks": [_task(1, "T", "2026-03-10", 1)], "today": "2026-03-10"})
        with self.assertRaises(ValueError):
            run_feature({"tasks": [{"pk": 1, "title": "T", "due_date": "2026-03-10"}], "today": "2026-03-10"})

    def test_invalid_calendar_dates(self):
        with self.assertRaises(ValueError):
            run_feature({"tasks": [], "today": "2026-13-01"})
        with self.assertRaises(ValueError):
            run_feature({"tasks": [], "today": "2026-02-29"})
        with self.assertRaises(ValueError):
            run_feature({"tasks": [_task(1, "T", "2026-02-30", False)], "today": "2026-03-10"})
        with self.assertRaises(ValueError):
            run_feature({"tasks": [_task(1, "T", "03-10-2026", False)], "today": "2026-03-10"})
        ok = run_feature({"tasks": [_task(1, "Leap", "2024-02-29", False)], "today": "2024-02-29", "status": "today", "q": ""})
        self.assertEqual(ok["filtered_count"], 1)
        with self.assertRaises(ValueError):
            run_feature({"tasks": [_task(1, "T", "2023-02-29", False)], "today": "2024-02-29"})

    def test_pure_deterministic_and_input_preserved(self):
        payload = {
            "tasks": [_task(2, "Bravo", "2026-03-11", False), _task(1, "Alpha", "2026-03-09", False)],
            "today": "2026-03-10",
            "status": "all",
            "q": "a",
        }
        snapshot = copy.deepcopy(payload)
        first = run_feature(payload)
        second = run_feature(payload)
        self.assertEqual(first, second)
        self.assertEqual(payload, snapshot)
        first["results"][0]["pk"] = 9999
        third = run_feature(payload)
        self.assertNotEqual(first["results"][0]["pk"], third["results"][0]["pk"])


if __name__ == "__main__":
    unittest.main()
