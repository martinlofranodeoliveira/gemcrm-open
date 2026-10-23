import copy
import unittest
from crm.features.task_duplicate_finder import run_feature
def _task(pk, title, due_date, deal=None, completed=False, extra=None):
    t = {"pk": pk, "title": title, "due_date": due_date, "deal": deal, "completed": completed}
    if extra is not None:
        for k in extra:
            t[k] = extra[k]
    return t
class TaskDuplicateFinderCommunityTest(unittest.TestCase):
    def test_empty_tasks(self):
        out = run_feature({"tasks": []})
        self.assertEqual(out, {"total_tasks": 0, "duplicate_group_count": 0, "duplicate_task_count": 0, "groups": []})
    def test_missing_tasks_defaults_empty(self):
        out = run_feature({})
        self.assertEqual(out["total_tasks"], 0)
        self.assertEqual(out["groups"], [])
    def test_singleton_never_groups(self):
        out = run_feature({"tasks": [_task(1, "Ligar", "2026-03-10", None)]})
        self.assertEqual(out["duplicate_group_count"], 0)
        self.assertEqual(out["duplicate_task_count"], 0)
        self.assertEqual(out["groups"], [])
    def test_contract_example_grouped(self):
        payload = {"tasks": [_task(1, " Retorno ", "2026-03-10", 2), _task(2, "retorno", "2026-03-10", 2), _task(3, "Retorno", "2026-03-11", 2)]}
        out = run_feature(payload)
        self.assertEqual(out["total_tasks"], 3)
        self.assertEqual(out["duplicate_group_count"], 1)
        self.assertEqual(out["duplicate_task_count"], 2)
        self.assertEqual(len(out["groups"]), 1)
        g = out["groups"][0]
        self.assertEqual(g["title_normalized"], "retorno")
        self.assertEqual(g["due_date"], "2026-03-10")
        self.assertEqual(g["deal"], 2)
        self.assertEqual(g["count"], 2)
        self.assertEqual(g["task_pks"], [1, 2])
    def test_contract_example_deal_separate(self):
        payload = {"tasks": [_task(1, "Ligar", "2026-03-10", None), _task(2, "Ligar", "2026-03-10", 5)]}
        out = run_feature(payload)
        self.assertEqual(out["total_tasks"], 2)
        self.assertEqual(out["duplicate_group_count"], 0)
        self.assertEqual(out["groups"], [])
    def test_different_date_stays_separate(self):
        payload = {"tasks": [_task(1, "Ligar", "2026-03-10"), _task(2, "Ligar", "2026-03-11")]}
        out = run_feature(payload)
        self.assertEqual(out["duplicate_group_count"], 0)
    def test_normalizes_strip_and_casefold(self):
        payload = {"tasks": [_task(1, " \t\nLIGAR\r ", "2026-04-01"), _task(2, "ligar", "2026-04-01")]}
        out = run_feature(payload)
        self.assertEqual(out["duplicate_group_count"], 1)
        self.assertEqual(out["groups"][0]["title_normalized"], "ligar")
    def test_task_pks_sorted_ascending(self):
        payload = {"tasks": [_task(9, "Dup", "2026-05-01"), _task(3, "dup", "2026-05-01"), _task(7, " DUP ", "2026-05-01")]}
        out = run_feature(payload)
        self.assertEqual(out["groups"][0]["task_pks"], [3, 7, 9])
    def test_groups_sorted_by_due_title_deal(self):
        payload = {"tasks": [_task(1, "b", "2026-03-12"), _task(2, "B", "2026-03-12"), _task(3, "a", "2026-03-10"), _task(4, "A", "2026-03-10"), _task(5, "x", "2026-03-10", 2), _task(6, "X", "2026-03-10", 2), _task(7, "x", "2026-03-10", 1), _task(8, "X", "2026-03-10", 1)]}
        out = run_feature(payload)
        self.assertEqual(out["duplicate_group_count"], 4)
        self.assertEqual(out["groups"][0]["due_date"], "2026-03-10")
        self.assertEqual(out["groups"][0]["title_normalized"], "a")
        self.assertEqual(out["groups"][1]["title_normalized"], "x")
        self.assertEqual(out["groups"][1]["deal"], 1)
        self.assertEqual(out["groups"][2]["deal"], 2)
        self.assertEqual(out["groups"][3]["due_date"], "2026-03-12")
    def test_null_deal_sorts_first(self):
        payload = {"tasks": [_task(1, "same", "2026-03-10", 5), _task(2, "SAME", "2026-03-10", 5), _task(3, "same", "2026-03-10", None), _task(4, "SAME", "2026-03-10", None)]}
        out = run_feature(payload)
        self.assertEqual(len(out["groups"]), 2)
        self.assertIsNone(out["groups"][0]["deal"])
        self.assertEqual(out["groups"][1]["deal"], 5)
    def test_leap_year_dates(self):
        ok = run_feature({"tasks": [_task(1, "a", "2024-02-29"), _task(2, "A", "2024-02-29")]})
        self.assertEqual(ok["duplicate_group_count"], 1)
        ok2 = run_feature({"tasks": [_task(1, "a", "2000-02-29"), _task(2, "A", "2000-02-29")]})
        self.assertEqual(ok2["duplicate_group_count"], 1)
        with self.assertRaises(ValueError):
            run_feature({"tasks": [_task(1, "a", "2023-02-29")]})
        with self.assertRaises(ValueError):
            run_feature({"tasks": [_task(1, "a", "1900-02-29")]})
        with self.assertRaises(ValueError):
            run_feature({"tasks": [_task(1, "a", "2026-13-01")]})
        with self.assertRaises(ValueError):
            run_feature({"tasks": [_task(1, "a", "2026-04-31")]})
        with self.assertRaises(ValueError):
            run_feature({"tasks": [_task(1, "a", "0000-01-01")]})
    def test_rejects_bad_payload_and_bounds(self):
        with self.assertRaises(ValueError):
            run_feature([])
        with self.assertRaises(ValueError):
            run_feature({"tasks": "nope"})
        with self.assertRaises(ValueError):
            run_feature({"tasks": [_task(True, "a", "2026-01-01")]})
        with self.assertRaises(ValueError):
            run_feature({"tasks": [_task(1, "a", "2026-01-01", True)]})
        with self.assertRaises(ValueError):
            run_feature({"tasks": [_task(1, "a", "2026-01-01", None, "no")]})
        with self.assertRaises(ValueError):
            run_feature({"tasks": [_task(1, "   ", "2026-01-01")]})
        with self.assertRaises(ValueError):
            run_feature({"tasks": [_task(1, "x" * 10001, "2026-01-01")]})
        with self.assertRaises(ValueError):
            run_feature({"tasks": [_task(1, "a", "2026-01-01"), _task(1, "b", "2026-01-02")]})
        many = [_task(i + 1, "t", "2026-01-01") for i in range(501)]
        with self.assertRaises(ValueError):
            run_feature({"tasks": many})
    def test_extra_keys_ignored(self):
        payload = {"tasks": [_task(1, "a", "2026-01-01", extra={"foo": 1})], "other": 99}
        out = run_feature(payload)
        self.assertEqual(out["total_tasks"], 1)
    def test_preserves_inputs_without_mutation(self):
        payload = {"tasks": [_task(2, " B ", "2026-03-10", 1), _task(1, "b", "2026-03-10", 1)], "extra": [1]}
        snapshot = copy.deepcopy(payload)
        first = run_feature(payload)
        second = run_feature(payload)
        self.assertEqual(payload, snapshot)
        self.assertEqual(first, second)
    def test_counts_sum(self):
        payload = {"tasks": [_task(1, "a", "2026-01-01"), _task(2, "A", "2026-01-01"), _task(3, "b", "2026-01-02"), _task(4, "B", "2026-01-02"), _task(5, "solo", "2026-01-03")]}
        out = run_feature(payload)
        self.assertEqual(out["total_tasks"], 5)
        self.assertEqual(out["duplicate_group_count"], 2)
        self.assertEqual(out["duplicate_task_count"], 4)
if __name__ == "__main__":
    unittest.main()
