import copy
import unittest

from crm.features.list_filter_state_keeper import run_feature


class ListFilterStateKeeperTests(unittest.TestCase):
    def test_contacts_example(self):
        result = run_feature({"q": "  Marina  ", "view": "contacts"})
        self.assertEqual(result, {
            "view": "contacts",
            "q": "Marina",
            "status": None,
            "preserved": {"q": "Marina"},
            "total_preserved": 1,
        })

    def test_tasks_bogus_status_falls_back_to_all(self):
        result = run_feature({"q": " retorno ", "status": "bogus", "view": "tasks"})
        self.assertEqual(result, {
            "view": "tasks",
            "q": "retorno",
            "status": "all",
            "preserved": {"q": "retorno"},
            "total_preserved": 1,
        })

    def test_rejects_none_and_non_dict(self):
        with self.assertRaises(ValueError):
            run_feature(None)
        for bad in ([], "tasks", 123, True, ({"view": "tasks"},)):
            with self.assertRaises(ValueError):
                run_feature(bad)

    def test_rejects_missing_and_invalid_view(self):
        with self.assertRaises(ValueError):
            run_feature({})
        with self.assertRaises(ValueError):
            run_feature({"q": "x"})
        for bad_view in (None, 123, "", "CONTACTS", "unknown"):
            with self.assertRaises(ValueError):
                run_feature({"view": bad_view})

    def test_ignores_extra_keys_and_does_not_mutate(self):
        payload = {"view": "tasks", "q": " a ", "status": "open", "extra": 1, "other": {"x": 1}}
        snapshot = copy.deepcopy(payload)
        result = run_feature(payload)
        self.assertEqual(payload, snapshot)
        self.assertEqual(result["preserved"], {"q": "a", "status": "open"})
        self.assertEqual(result["total_preserved"], 2)

    def test_q_defaults_and_normalization(self):
        self.assertEqual(run_feature({"view": "contacts"})["q"], "")
        self.assertEqual(run_feature({"view": "contacts", "q": None})["q"], "")
        self.assertEqual(run_feature({"view": "contacts", "q": "   "})["preserved"], {})
        long_q = "  " + ("x" * 500) + "  "
        result = run_feature({"view": "contacts", "q": long_q})
        self.assertEqual(result["q"], "x" * 200)
        self.assertEqual(result["preserved"], {"q": "x" * 200})
        for bad_q in (123, ["x"], {"x": 1}, True):
            with self.assertRaises(ValueError):
                run_feature({"view": "contacts", "q": bad_q})

    def test_tasks_status_mapping(self):
        self.assertEqual(run_feature({"view": "tasks"})["status"], "all")
        self.assertEqual(run_feature({"view": "tasks", "status": None})["status"], "all")
        self.assertEqual(run_feature({"view": "tasks", "status": ""})["status"], "all")
        for known in ("open", "overdue", "today", "upcoming", "completed", "all"):
            self.assertEqual(run_feature({"view": "tasks", "status": known})["status"], known)
        for unknown in ("bogus", "OPEN", " done "):
            self.assertEqual(run_feature({"view": "tasks", "status": unknown})["status"], "all")
        for bad in (123, ["open"], {"s": 1}, True):
            with self.assertRaises(ValueError):
                run_feature({"view": "tasks", "status": bad})

    def test_contacts_status_ignored(self):
        for raw in (None, "", "open", 123, ["x"], {"a": 1}, True):
            result = run_feature({"view": "contacts", "q": "", "status": raw})
            self.assertIsNone(result["status"])
            self.assertEqual(result["preserved"], {})
            self.assertEqual(result["total_preserved"], 0)

    def test_preserved_rules(self):
        self.assertEqual(run_feature({"view": "contacts"})["preserved"], {})
        self.assertEqual(run_feature({"view": "tasks"})["preserved"], {})
        self.assertEqual(run_feature({"view": "tasks", "status": "open"})["preserved"], {"status": "open"})
        result = run_feature({"view": "tasks", "q": " hi ", "status": "today"})
        self.assertEqual(result["preserved"], {"q": "hi", "status": "today"})
        self.assertEqual(result["total_preserved"], len(result["preserved"]))

    def test_deterministic(self):
        payload = {"view": "tasks", "q": " retorno ", "status": "bogus"}
        first = run_feature(dict(payload))
        second = run_feature(dict(payload))
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
