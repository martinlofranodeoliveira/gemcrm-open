import copy
import unittest
from crm.features.task_closed_deal_stale_triage import run_feature


class TaskClosedDealStaleTriageTests(unittest.TestCase):
    def test_main_example_buckets(self):
        payload = {"deals": [{"pk": 10, "stage": "won"}, {"pk": 11, "stage": "proposal"}], "tasks": [{"pk": 1, "title": "Retorno", "completed": False, "deal_pk": 10}, {"pk": 2, "title": "Proposta", "completed": False, "deal_pk": 11}, {"pk": 3, "title": "Ligar", "completed": False, "deal_pk": None}, {"pk": 4, "title": "Feito", "completed": True, "deal_pk": 10}]}
        result = run_feature(payload)
        self.assertEqual(result["task_count"], 4)
        self.assertEqual(result["open_count"], 3)
        self.assertEqual(result["completed_count"], 1)
        self.assertEqual(result["stale_pks"], [1])
        self.assertEqual(result["open_linked_pks"], [2])
        self.assertEqual(result["unlinked_pks"], [3])
        self.assertEqual(result["completed_pks"], [4])
        self.assertEqual(result["unknown_pks"], [])
        self.assertEqual(result["stale_count"], 1)
        self.assertEqual(result["open_linked_count"], 1)
        self.assertEqual(result["unlinked_count"], 1)
        self.assertEqual(result["unknown_count"], 0)

    def test_well_formed_identifier_shortcut_unknown(self):
        payload = {"deals": [{"pk": 10, "stage": "lost"}], "tasks": [{"pk": 5, "title": "Cobrar", "completed": False, "deal_pk": 99}]}
        result = run_feature(payload)
        self.assertEqual(result["unknown_pks"], [5])
        self.assertEqual(result["stale_pks"], [])
        self.assertEqual(result["stale_count"], 0)
        self.assertEqual(result["unknown_count"], 1)
        self.assertEqual(result["open_count"], 1)

    def test_completed_linked_to_closed_never_stale(self):
        payload = {"deals": [{"pk": 20, "stage": "lost"}], "tasks": [{"pk": 6, "title": "Ok", "completed": True, "deal_pk": 20}]}
        result = run_feature(payload)
        self.assertEqual(result["completed_pks"], [6])
        self.assertEqual(result["stale_pks"], [])
        self.assertEqual(result["open_count"], 0)
        self.assertEqual(result["completed_count"], 1)

    def test_empty_input_all_zero(self):
        result = run_feature({})
        self.assertEqual(result, {"task_count": 0, "open_count": 0, "completed_count": 0, "stale_count": 0, "open_linked_count": 0, "unlinked_count": 0, "unknown_count": 0, "stale_pks": [], "open_linked_pks": [], "unlinked_pks": [], "unknown_pks": [], "completed_pks": []})
        result2 = run_feature({"tasks": [], "deals": []})
        self.assertEqual(result2["task_count"], 0)
        self.assertEqual(result2["open_count"], 0)

    def test_sorting_and_counts_consistent(self):
        payload = {"deals": [{"pk": 30, "stage": "won"}, {"pk": 31, "stage": "new"}], "tasks": [{"pk": 9, "title": "B", "completed": False, "deal_pk": 30}, {"pk": 7, "title": "A", "completed": False, "deal_pk": 30}, {"pk": 12, "title": "C", "completed": False, "deal_pk": 31}, {"pk": 11, "title": "D", "completed": False, "deal_pk": 31}, {"pk": 20, "title": "E", "completed": False, "deal_pk": None}, {"pk": 18, "title": "F", "completed": False, "deal_pk": None}]}
        result = run_feature(payload)
        self.assertEqual(result["stale_pks"], [7, 9])
        self.assertEqual(result["open_linked_pks"], [11, 12])
        self.assertEqual(result["unlinked_pks"], [18, 20])
        self.assertEqual(result["stale_count"], len(result["stale_pks"]))
        self.assertEqual(result["open_linked_count"], len(result["open_linked_pks"]))
        self.assertEqual(result["unlinked_count"], len(result["unlinked_pks"]))
        self.assertEqual(result["unknown_count"], len(result["unknown_pks"]))
        self.assertEqual(result["completed_count"], len(result["completed_pks"]))
        self.assertEqual(result["open_count"], result["stale_count"] + result["open_linked_count"] + result["unlinked_count"] + result["unknown_count"])
        self.assertEqual(result["task_count"], result["open_count"] + result["completed_count"])

    def test_open_stages_mapping(self):
        payload = {"deals": [{"pk": 1, "stage": "new"}, {"pk": 2, "stage": "qualified"}, {"pk": 3, "stage": "proposal"}, {"pk": 4, "stage": "won"}, {"pk": 5, "stage": "lost"}], "tasks": [{"pk": 1, "title": "a", "completed": False, "deal_pk": 1}, {"pk": 2, "title": "b", "completed": False, "deal_pk": 2}, {"pk": 3, "title": "c", "completed": False, "deal_pk": 3}, {"pk": 4, "title": "d", "completed": False, "deal_pk": 4}, {"pk": 5, "title": "e", "completed": False, "deal_pk": 5}]}
        result = run_feature(payload)
        self.assertEqual(result["open_linked_pks"], [1, 2, 3])
        self.assertEqual(result["stale_pks"], [4, 5])

    def test_extra_keys_ignored_and_defaults(self):
        payload = {"tasks": [{"pk": 1, "title": "Hi", "completed": False, "deal_pk": None, "other": 1}], "deals": [], "extra": "yes"}
        result = run_feature(payload)
        self.assertEqual(result["unlinked_pks"], [1])
        payload2 = {"deals": [{"pk": 1, "stage": "new", "note": "x"}]}
        result2 = run_feature(payload2)
        self.assertEqual(result2["task_count"], 0)

    def test_preserves_inputs_without_mutation(self):
        payload = {"deals": [{"pk": 10, "stage": "won"}], "tasks": [{"pk": 1, "title": "Retorno", "completed": False, "deal_pk": 10}]}
        before = copy.deepcopy(payload)
        run_feature(payload)
        self.assertEqual(payload, before)

    def test_pure_deterministic(self):
        payload = {"deals": [{"pk": 10, "stage": "won"}], "tasks": [{"pk": 1, "title": "A", "completed": False, "deal_pk": 10}]}
        first = run_feature(payload)
        second = run_feature(payload)
        self.assertEqual(first, second)

    def test_malformed_payload(self):
        for bad in (None, [], "x", 1, True):
            with self.assertRaises(ValueError):
                run_feature(bad)
        for bad_tasks in (None, "x", {}, 5):
            with self.assertRaises(ValueError):
                run_feature({"tasks": bad_tasks, "deals": []})
        for bad_deals in (None, "x", {}, 5):
            with self.assertRaises(ValueError):
                run_feature({"tasks": [], "deals": bad_deals})
        with self.assertRaises(ValueError):
            run_feature({"tasks": [1] * 101, "deals": []})
        with self.assertRaises(ValueError):
            run_feature({"tasks": [], "deals": [{"pk": 1, "stage": "new"}] * 101})

    def test_malformed_tasks(self):
        with self.assertRaises(ValueError):
            run_feature({"tasks": ["x"], "deals": []})
        with self.assertRaises(ValueError):
            run_feature({"tasks": [{"title": "a", "completed": False, "deal_pk": None}], "deals": []})
        with self.assertRaises(ValueError):
            run_feature({"tasks": [{"pk": True, "title": "a", "completed": False, "deal_pk": None}], "deals": []})
        with self.assertRaises(ValueError):
            run_feature({"tasks": [{"pk": 0, "title": "a", "completed": False, "deal_pk": None}], "deals": []})
        with self.assertRaises(ValueError):
            run_feature({"tasks": [{"pk": 9007199254740992, "title": "a", "completed": False, "deal_pk": None}], "deals": []})
        with self.assertRaises(ValueError):
            run_feature({"tasks": [{"pk": 1, "title": "", "completed": False, "deal_pk": None}], "deals": []})
        with self.assertRaises(ValueError):
            run_feature({"tasks": [{"pk": 1, "title": "x" * 181, "completed": False, "deal_pk": None}], "deals": []})
        with self.assertRaises(ValueError):
            run_feature({"tasks": [{"pk": 1, "title": "a", "completed": 1, "deal_pk": None}], "deals": []})
        with self.assertRaises(ValueError):
            run_feature({"tasks": [{"pk": 1, "title": "a", "completed": False, "deal_pk": True}], "deals": []})
        with self.assertRaises(ValueError):
            run_feature({"tasks": [{"pk": 1, "title": "a", "completed": False}], "deals": []})
        with self.assertRaises(ValueError):
            run_feature({"tasks": [{"pk": 1, "title": "a", "completed": False, "deal_pk": None}, {"pk": 1, "title": "b", "completed": False, "deal_pk": None}], "deals": []})

    def test_malformed_deals(self):
        with self.assertRaises(ValueError):
            run_feature({"tasks": [], "deals": ["x"]})
        with self.assertRaises(ValueError):
            run_feature({"tasks": [], "deals": [{"stage": "new"}]})
        with self.assertRaises(ValueError):
            run_feature({"tasks": [], "deals": [{"pk": 1}]})
        with self.assertRaises(ValueError):
            run_feature({"tasks": [], "deals": [{"pk": 1, "stage": "closed"}]})
        with self.assertRaises(ValueError):
            run_feature({"tasks": [], "deals": [{"pk": 1, "stage": "new"}, {"pk": 1, "stage": "won"}]})
        with self.assertRaises(ValueError):
            run_feature({"tasks": [], "deals": [{"pk": False, "stage": "new"}]})


if __name__ == "__main__":
    unittest.main()
