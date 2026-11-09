import copy
import unittest

from crm.features.contact_activity_timeline import run_feature


class ContactActivityTimelineTests(unittest.TestCase):
    def test_mixed_snapshot_filters_and_orders_deals(self):
        payload = {
            "contact": {"pk": 1, "name": "Marina"},
            "deals": [
                {"pk": 10, "title": "Site", "stage": "new", "contact_pk": 1},
                {"pk": 11, "title": "Loja", "stage": "won", "contact_pk": 2},
            ],
            "tasks": [
                {"pk": 5, "title": "Ligar", "due_date": "2026-02-10", "completed": False, "deal_pk": 10},
                {"pk": 6, "title": "Visita", "due_date": "2026-02-09", "completed": False, "deal_pk": 11},
            ],
        }
        result = run_feature(payload)
        self.assertEqual(result["contact_pk"], 1)
        self.assertEqual(result["contact_name"], "Marina")
        self.assertEqual(result["deal_count"], 2)
        self.assertEqual(result["linked_deal_count"], 1)
        self.assertEqual(result["linked_deals"], [{"pk": 10, "title": "Site", "stage": "new"}])
        self.assertEqual(result["task_count"], 2)
        self.assertEqual(result["linked_task_count"], 1)
        self.assertEqual(result["linked_tasks"], [{"pk": 5, "title": "Ligar", "due_date": "2026-02-10", "completed": False, "deal_pk": 10}])

    def test_task_sort_lexical_then_pk_and_excludes_unrelated(self):
        payload = {
            "contact": {"pk": 3, "name": "Ana"},
            "deals": [
                {"pk": 20, "title": "B", "stage": "proposal", "contact_pk": 3},
                {"pk": 10, "title": "A", "stage": "qualified", "contact_pk": 3},
                {"pk": 30, "title": "C", "stage": "new", "contact_pk": None},
            ],
            "tasks": [
                {"pk": 8, "title": "T2", "due_date": "2026-03-02", "completed": True, "deal_pk": 10},
                {"pk": 7, "title": "T1", "due_date": "2026-03-01", "completed": False, "deal_pk": 10},
                {"pk": 9, "title": "T3", "due_date": "2026-03-01", "completed": False, "deal_pk": 30},
            ],
        }
        result = run_feature(payload)
        self.assertEqual(result["linked_deals"], [
            {"pk": 10, "title": "A", "stage": "qualified"},
            {"pk": 20, "title": "B", "stage": "proposal"},
        ])
        self.assertEqual(result["linked_tasks"], [
            {"pk": 7, "title": "T1", "due_date": "2026-03-01", "completed": False, "deal_pk": 10},
            {"pk": 8, "title": "T2", "due_date": "2026-03-02", "completed": True, "deal_pk": 10},
        ])

    def test_empty_returns_zero(self):
        result = run_feature({"contact": {"pk": 2, "name": "Jo"}, "deals": [], "tasks": []})
        self.assertEqual(result, {
            "contact_pk": 2,
            "contact_name": "Jo",
            "deal_count": 0,
            "task_count": 0,
            "linked_deal_count": 0,
            "linked_task_count": 0,
            "linked_deals": [],
            "linked_tasks": [],
        })

    def test_missing_lists_default_to_empty(self):
        result = run_feature({"contact": {"pk": 2, "name": "Jo"}})
        self.assertEqual(result["deal_count"], 0)
        self.assertEqual(result["linked_deals"], [])
        self.assertEqual(result["linked_tasks"], [])

    def test_null_deal_pk_tasks_excluded(self):
        payload = {
            "contact": {"pk": 1, "name": "Marina"},
            "deals": [{"pk": 10, "title": "Site", "stage": "new", "contact_pk": 1}],
            "tasks": [
                {"pk": 1, "title": "A", "due_date": "2026-01-01", "completed": False, "deal_pk": None},
                {"pk": 2, "title": "B", "due_date": "2026-01-02", "completed": False, "deal_pk": 10},
            ],
        }
        result = run_feature(payload)
        self.assertEqual(len(result["linked_tasks"]), 1)
        self.assertEqual(result["linked_tasks"][0]["pk"], 2)

    def test_tie_date_orders_only_by_pk(self):
        payload = {
            "contact": {"pk": 1, "name": "Marina"},
            "deals": [{"pk": 10, "title": "Site", "stage": "new", "contact_pk": 1}],
            "tasks": [
                {"pk": 30, "title": "C", "due_date": "2026-05-01", "completed": False, "deal_pk": 10},
                {"pk": 20, "title": "B", "due_date": "2026-05-01", "completed": True, "deal_pk": 10},
                {"pk": 10, "title": "A", "due_date": "2026-05-01", "completed": False, "deal_pk": 10},
            ],
        }
        result = run_feature(payload)
        self.assertEqual([t["pk"] for t in result["linked_tasks"]], [10, 20, 30])

    def test_malformed_inputs_raise_and_preserve(self):
        good_deal = {"pk": 10, "title": "Site", "stage": "new", "contact_pk": 1}
        good_task = {"pk": 5, "title": "Ligar", "due_date": "2026-02-10", "completed": False, "deal_pk": 10}
        bad_payloads = [
            None,
            [],
            {},
            {"contact": None},
            {"contact": {"pk": True, "name": "A"}},
            {"contact": {"pk": 0, "name": "A"}},
            {"contact": {"pk": 1, "name": ""}},
            {"contact": {"pk": 1}},
            {"contact": {"name": "A"}},
            {"contact": {"pk": 1, "name": "A"}, "deals": None},
            {"contact": {"pk": 1, "name": "A"}, "tasks": None},
            {"contact": {"pk": 1, "name": "A"}, "deals": {}, "tasks": []},
            {"contact": {"pk": 1, "name": "A"}, "deals": [{"pk": 1, "title": "T", "stage": "bogus", "contact_pk": 1}]},
            {"contact": {"pk": 1, "name": "A"}, "deals": [{"pk": 1, "title": "T", "stage": "new", "contact_pk": 1}], "tasks": [{"pk": 1, "title": "T", "due_date": "2026-02-30", "completed": False, "deal_pk": 1}]},
            {"contact": {"pk": 1, "name": "A"}, "deals": [{"pk": 1, "title": "T", "stage": "new", "contact_pk": 1}], "tasks": [{"pk": 1, "title": "T", "due_date": "2023-02-29", "completed": False, "deal_pk": 1}]},
            {"contact": {"pk": 1, "name": "A"}, "deals": [{"pk": 1, "title": "T", "stage": "new", "contact_pk": 1}], "tasks": [{"pk": 1, "title": "T", "due_date": "2026-02-10", "completed": 0, "deal_pk": 1}]},
            {"contact": {"pk": 1, "name": "A"}, "deals": [{"pk": 1, "title": "T", "stage": "new", "contact_pk": 1}, {"pk": 1, "title": "U", "stage": "new", "contact_pk": 1}]},
        ]
        for bad in bad_payloads:
            snapshot = copy.deepcopy(bad)
            with self.assertRaises(ValueError):
                run_feature(bad)
            self.assertEqual(bad, snapshot)

    def test_duplicate_task_pk_and_limits(self):
        base = {"contact": {"pk": 1, "name": "A"}, "deals": [{"pk": 1, "title": "T", "stage": "new", "contact_pk": 1}]}
        dup = copy.deepcopy(base)
        dup["tasks"] = [
            {"pk": 1, "title": "A", "due_date": "2026-01-01", "completed": False, "deal_pk": 1},
            {"pk": 1, "title": "B", "due_date": "2026-01-02", "completed": False, "deal_pk": 1},
        ]
        snap = copy.deepcopy(dup)
        with self.assertRaises(ValueError):
            run_feature(dup)
        self.assertEqual(dup, snap)
        many_deals = copy.deepcopy(base)
        many_deals["deals"] = [{"pk": i + 1, "title": "T", "stage": "new", "contact_pk": 1} for i in range(101)]
        with self.assertRaises(ValueError):
            run_feature(many_deals)
        many_tasks = copy.deepcopy(base)
        many_tasks["tasks"] = [{"pk": i + 1, "title": "T", "due_date": "2026-01-01", "completed": False, "deal_pk": 1} for i in range(201)]
        with self.assertRaises(ValueError):
            run_feature(many_tasks)

    def test_leap_day_accepted_and_extra_keys_ignored(self):
        payload = {
            "contact": {"pk": 1, "name": "Ana", "extra": "ignore"},
            "deals": [{"pk": 5, "title": "X", "stage": "new", "contact_pk": 1, "junk": 1}],
            "tasks": [{"pk": 7, "title": "Y", "due_date": "2024-02-29", "completed": False, "deal_pk": 5, "junk": 2}],
            "extra": 99,
        }
        snapshot = copy.deepcopy(payload)
        result = run_feature(payload)
        self.assertEqual(result["linked_task_count"], 1)
        self.assertEqual(payload, snapshot)

    def test_inputs_not_mutated_on_success(self):
        payload = {
            "contact": {"pk": 3, "name": "Ana"},
            "deals": [{"pk": 20, "title": "B", "stage": "proposal", "contact_pk": 3}],
            "tasks": [{"pk": 7, "title": "T1", "due_date": "2026-03-01", "completed": False, "deal_pk": 20}],
        }
        snapshot = copy.deepcopy(payload)
        run_feature(payload)
        self.assertEqual(payload, snapshot)


if __name__ == "__main__":
    unittest.main()
