import copy
import unittest
from crm.features.task_draft_validator import run_feature

class TaskDraftValidatorCommunityTest(unittest.TestCase):
    def test_valid_basic(self):
        payload = {"title": "Retornar para Marina", "due_date": "2026-03-10", "completed": False, "deal_pk": None}
        result = run_feature(payload)
        self.assertTrue(result["valid"])
        self.assertEqual(result["errors"], {})
        self.assertEqual(result["normalized"], {"title": "Retornar para Marina", "due_date": "2026-03-10", "completed": False, "deal_pk": None})

    def test_valid_trimmed_and_defaults(self):
        payload = {"title": "  Ligar amanha \t\n", "due_date": "2024-02-29"}
        snapshot = copy.deepcopy(payload)
        result = run_feature(payload)
        self.assertTrue(result["valid"])
        self.assertEqual(result["normalized"]["title"], "Ligar amanha")
        self.assertEqual(result["normalized"]["due_date"], "2024-02-29")
        self.assertIs(result["normalized"]["completed"], False)
        self.assertIs(result["normalized"]["deal_pk"], None)
        self.assertEqual(payload, snapshot)

    def test_valid_with_deal_and_extra_keys(self):
        payload = {"title": "Follow", "due_date": "2026-01-31", "completed": True, "deal_pk": 9007199254740991, "extra": "ignored"}
        result = run_feature(payload)
        self.assertTrue(result["valid"])
        self.assertEqual(result["normalized"], {"title": "Follow", "due_date": "2026-01-31", "completed": True, "deal_pk": 9007199254740991})

    def test_title_errors(self):
        r1 = run_feature({"title": "  ", "due_date": "2026-03-10"})
        self.assertFalse(r1["valid"])
        self.assertEqual(r1["errors"]["title"], "title is required")
        self.assertIs(r1["normalized"], None)
        r2 = run_feature({"due_date": "2026-03-10"})
        self.assertEqual(r2["errors"]["title"], "title is required")
        r3 = run_feature({"title": None, "due_date": "2026-03-10"})
        self.assertEqual(r3["errors"]["title"], "title is required")
        r4 = run_feature({"title": 123, "due_date": "2026-03-10"})
        self.assertEqual(r4["errors"]["title"], "title must be a string")
        r5 = run_feature({"title": "x" * 181, "due_date": "2026-03-10"})
        self.assertEqual(r5["errors"]["title"], "title must be at most 180 characters")
        r6 = run_feature({"title": "y" * 180, "due_date": "2026-03-10"})
        self.assertTrue(r6["valid"])

    def test_due_date_errors(self):
        for bad in [None, ""]:
            r = run_feature({"title": "Ok", "due_date": bad})
            self.assertEqual(r["errors"]["due_date"], "due_date is required")
        r = run_feature({"title": "Ok"})
        self.assertEqual(r["errors"]["due_date"], "due_date is required")
        for bad in ["2026-02-30", "2026-13-01", "2026-00-10", "2026/03/10", "2026-3-10", "not-a-date", 20260310, "2023-02-29"]:
            rr = run_feature({"title": "Ok", "due_date": bad})
            self.assertFalse(rr["valid"], msg=bad)
            self.assertEqual(rr["errors"]["due_date"], "due_date must be YYYY-MM-DD valid calendar date")
            self.assertIs(rr["normalized"], None)
        ok_leap = run_feature({"title": "Ok", "due_date": "2000-02-29"})
        self.assertTrue(ok_leap["valid"])
        bad_century = run_feature({"title": "Ok", "due_date": "1900-02-29"})
        self.assertEqual(bad_century["errors"]["due_date"], "due_date must be YYYY-MM-DD valid calendar date")

    def test_completed_and_deal_errors(self):
        r = run_feature({"title": "Ligar amanha", "due_date": "2024-02-29", "completed": 0, "deal_pk": 0})
        self.assertFalse(r["valid"])
        self.assertEqual(r["errors"]["completed"], "completed must be a boolean")
        self.assertEqual(r["errors"]["deal_pk"], "deal_pk must be an integer 1 to 9007199254740991 or null")
        for bad_c in [0, 1, "false", None, 0.0]:
            rr = run_feature({"title": "Ok", "due_date": "2026-03-10", "completed": bad_c})
            self.assertEqual(rr["errors"]["completed"], "completed must be a boolean")
        for bad_d in [0, -1, 9007199254740992, True, False, "5", 1.5]:
            rr = run_feature({"title": "Ok", "due_date": "2026-03-10", "deal_pk": bad_d})
            self.assertEqual(rr["errors"]["deal_pk"], "deal_pk must be an integer 1 to 9007199254740991 or null", msg=repr(bad_d))

    def test_non_object_raises_and_no_mutation(self):
        for bad in [None, [], "x", 123, True]:
            with self.assertRaises(ValueError):
                run_feature(bad)
        payload = {"title": "  Keep  ", "due_date": "2026-03-10", "completed": False, "deal_pk": 7}
        snapshot = copy.deepcopy(payload)
        result = run_feature(payload)
        self.assertTrue(result["valid"])
        self.assertEqual(payload, snapshot)
        payload2 = {"title": "  ", "due_date": "2026-02-30", "completed": 0, "deal_pk": 0}
        snapshot2 = copy.deepcopy(payload2)
        result2 = run_feature(payload2)
        self.assertFalse(result2["valid"])
        self.assertEqual(payload2, snapshot2)
        self.assertIn("title", result2["errors"])
        self.assertIn("due_date", result2["errors"])

if __name__ == "__main__":
    unittest.main()
