import copy
import json
import unittest

from crm.features.deal_stage_transition_guard import run_feature


class DealStageTransitionGuardTests(unittest.TestCase):
    def test_same_stage_open_noop(self):
        result = run_feature({"current_stage": "new", "next_stage": "new"})
        self.assertEqual(result, {"current_stage": "new", "next_stage": "new", "valid": True, "changed": False, "terminal": False, "close": False, "reason": "noop"})

    def test_same_stage_closed_noop_terminal(self):
        for stage in ("won", "lost"):
            with self.subTest(stage=stage):
                result = run_feature({"current_stage": stage, "next_stage": stage})
                self.assertTrue(result["valid"])
                self.assertFalse(result["changed"])
                self.assertFalse(result["close"])
                self.assertEqual(result["reason"], "noop")
                self.assertTrue(result["terminal"])

    def test_open_to_open_progress(self):
        cases = [("new", "qualified"), ("new", "proposal"), ("qualified", "proposal"), ("proposal", "new")]
        for current_stage, next_stage in cases:
            with self.subTest(current_stage=current_stage, next_stage=next_stage):
                result = run_feature({"current_stage": current_stage, "next_stage": next_stage})
                self.assertEqual(result, {"current_stage": current_stage, "next_stage": next_stage, "valid": True, "changed": True, "terminal": False, "close": False, "reason": "progress"})

    def test_open_to_closed_close(self):
        for current_stage in ("new", "qualified", "proposal"):
            for next_stage in ("won", "lost"):
                with self.subTest(current_stage=current_stage, next_stage=next_stage):
                    result = run_feature({"current_stage": current_stage, "next_stage": next_stage})
                    self.assertEqual(result, {"current_stage": current_stage, "next_stage": next_stage, "valid": True, "changed": True, "terminal": False, "close": True, "reason": "close"})

    def test_closed_to_different_blocked(self):
        cases = [("won", "lost"), ("won", "new"), ("won", "proposal"), ("lost", "won"), ("lost", "new"), ("lost", "qualified")]
        for current_stage, next_stage in cases:
            with self.subTest(current_stage=current_stage, next_stage=next_stage):
                result = run_feature({"current_stage": current_stage, "next_stage": next_stage})
                self.assertEqual(result, {"current_stage": current_stage, "next_stage": next_stage, "valid": False, "changed": True, "terminal": True, "close": False, "reason": "terminal_blocked"})

    def test_contract_examples(self):
        self.assertEqual(run_feature({"current_stage": "new", "next_stage": "proposal"}), {"changed": True, "close": False, "current_stage": "new", "next_stage": "proposal", "reason": "progress", "terminal": False, "valid": True})
        self.assertEqual(run_feature({"current_stage": "qualified", "next_stage": "won"}), {"changed": True, "close": True, "current_stage": "qualified", "next_stage": "won", "reason": "close", "terminal": False, "valid": True})
        self.assertEqual(run_feature({"current_stage": "won", "next_stage": "lost"}), {"changed": True, "close": False, "current_stage": "won", "next_stage": "lost", "reason": "terminal_blocked", "terminal": True, "valid": False})

    def test_invalid_payloads_raise_value_error(self):
        bad_payloads = [None, [], "new", 42, True, [{"current_stage": "new", "next_stage": "won"}], {}, {"current_stage": "new"}, {"next_stage": "won"}, {"current_stage": "new", "next_stage": "won", "extra": 1}]
        # last entry is valid and checked elsewhere; keep invalid list without it
        for payload in bad_payloads[:9]:
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    run_feature(payload)
        bad_stages = [{"current_stage": None, "next_stage": "won"}, {"current_stage": "new", "next_stage": None}, {"current_stage": 1, "next_stage": "won"}, {"current_stage": "new", "next_stage": ["won"]}, {"current_stage": "NEW", "next_stage": "won"}, {"current_stage": "new", "next_stage": "closed"}, {"current_stage": "", "next_stage": "won"}]
        for payload in bad_stages:
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    run_feature(payload)

    def test_extra_keys_ignored_and_input_not_mutated(self):
        payload = {"current_stage": "new", "next_stage": "proposal", "extra": "ignore-me", "owner": 7}
        snapshot = copy.deepcopy(payload)
        result = run_feature(payload)
        self.assertEqual(payload, snapshot)
        self.assertEqual(result["reason"], "progress")
        self.assertTrue(result["valid"])
        payload2 = {"current_stage": "qualified", "next_stage": "qualified"}
        snapshot2 = copy.deepcopy(payload2)
        result2 = run_feature(payload2)
        self.assertEqual(payload2, snapshot2)
        self.assertEqual(result2["reason"], "noop")

    def test_deterministic_pure_json(self):
        payload = {"current_stage": "qualified", "next_stage": "lost"}
        first = run_feature(dict(payload))
        second = run_feature(dict(payload))
        self.assertEqual(first, second)
        text = json.dumps(first, sort_keys=True)
        self.assertEqual(json.loads(text), first)


if __name__ == "__main__":
    unittest.main()
