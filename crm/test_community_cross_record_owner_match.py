import ast
import copy
import inspect
import unittest

from crm.features.cross_record_owner_match import run_feature
import crm.features.cross_record_owner_match as core_module

MESSAGE = "Escolha um registro da sua conta."


class CrossRecordOwnerMatchTests(unittest.TestCase):
    def test_matching_with_null_keeps_valid(self):
        payload = {
            "owner_id": 7,
            "links": [
                {"field": "company", "related_owner_id": 7},
                {"field": "contact", "related_owner_id": None},
            ],
        }
        snapshot = copy.deepcopy(payload)
        result = run_feature(payload)
        self.assertEqual(result, {"owner_id": 7, "checked": 2, "violated": 0, "valid": True, "errors": {}})
        self.assertEqual(payload, snapshot)

    def test_single_mismatched_deal(self):
        payload = {"owner_id": 7, "links": [{"field": "deal", "related_owner_id": 9}]}
        snapshot = copy.deepcopy(payload)
        result = run_feature(payload)
        self.assertEqual(result["checked"], 1)
        self.assertEqual(result["violated"], 1)
        self.assertEqual(result["valid"], False)
        self.assertEqual(result["owner_id"], 7)
        self.assertEqual(result["errors"], {"deal": MESSAGE})
        self.assertEqual(payload, snapshot)

    def test_missing_links_defaults_empty(self):
        result = run_feature({"owner_id": 5})
        self.assertEqual(result, {"owner_id": 5, "checked": 0, "violated": 0, "valid": True, "errors": {}})

    def test_none_links_raises(self):
        payload = {"owner_id": 5, "links": None}
        snapshot = copy.deepcopy(payload)
        with self.assertRaises(ValueError):
            run_feature(payload)
        self.assertEqual(payload, snapshot)

    def test_non_dict_payload_raises(self):
        for bad in (None, [], "x", 5, [{"owner_id": 1}]):
            with self.assertRaises(ValueError):
                run_feature(bad)

    def test_boolean_ids_raise(self):
        with self.assertRaises(ValueError):
            run_feature({"owner_id": True, "links": []})
        with self.assertRaises(ValueError):
            run_feature({"owner_id": False})
        with self.assertRaises(ValueError):
            run_feature({"owner_id": 1, "links": [{"field": "company", "related_owner_id": True}]})
        with self.assertRaises(ValueError):
            run_feature({"owner_id": 1, "links": [{"field": "deal", "related_owner_id": False}]})

    def test_unknown_field_raises(self):
        payload = {"owner_id": 1, "links": [{"field": "task", "related_owner_id": 1}]}
        snapshot = copy.deepcopy(payload)
        with self.assertRaises(ValueError):
            run_feature(payload)
        self.assertEqual(payload, snapshot)

    def test_missing_field_raises(self):
        payload = {"owner_id": 1, "links": [{"related_owner_id": 1}]}
        snapshot = copy.deepcopy(payload)
        with self.assertRaises(ValueError):
            run_feature(payload)
        self.assertEqual(payload, snapshot)

    def test_duplicate_fields_raise(self):
        payload = {
            "owner_id": 1,
            "links": [
                {"field": "company", "related_owner_id": 1},
                {"field": "company", "related_owner_id": 1},
            ],
        }
        snapshot = copy.deepcopy(payload)
        with self.assertRaises(ValueError):
            run_feature(payload)
        self.assertEqual(payload, snapshot)

    def test_related_ids_below_one_raise(self):
        for bad in (0, -1, -50):
            payload = {"owner_id": 1, "links": [{"field": "contact", "related_owner_id": bad}]}
            snapshot = copy.deepcopy(payload)
            with self.assertRaises(ValueError):
                run_feature(payload)
            self.assertEqual(payload, snapshot)
        with self.assertRaises(ValueError):
            run_feature({"owner_id": 0, "links": []})
        with self.assertRaises(ValueError):
            run_feature({"owner_id": -3})

    def test_extra_keys_ignored_and_missing_related_defaults_none(self):
        payload = {"owner_id": 4, "links": [{"field": "contact"}], "extra": 123}
        result = run_feature(payload)
        self.assertEqual(result, {"owner_id": 4, "checked": 1, "violated": 0, "valid": True, "errors": {}})
        payload2 = {"owner_id": 4, "links": [{"field": "company", "related_owner_id": 4, "note": "x"}]}
        result2 = run_feature(payload2)
        self.assertEqual(result2["valid"], True)

    def test_inputs_unmutated_on_success_and_failure(self):
        good = {"owner_id": 7, "links": [{"field": "deal", "related_owner_id": 9}]}
        good_snapshot = copy.deepcopy(good)
        run_feature(good)
        self.assertEqual(good, good_snapshot)
        bad = {"owner_id": 7, "links": [{"field": "deal", "related_owner_id": 0}]}
        bad_snapshot = copy.deepcopy(bad)
        with self.assertRaises(ValueError):
            run_feature(bad)
        self.assertEqual(bad, bad_snapshot)

    def test_deterministic_and_counts(self):
        payload = {
            "owner_id": 2,
            "links": [
                {"field": "company", "related_owner_id": 2},
                {"field": "contact", "related_owner_id": 3},
                {"field": "deal", "related_owner_id": None},
            ],
        }
        first = run_feature(payload)
        second = run_feature(copy.deepcopy(payload))
        self.assertEqual(first, second)
        self.assertEqual(first["checked"], 3)
        self.assertEqual(first["violated"], 1)
        self.assertEqual(first["valid"], False)
        self.assertEqual(first["errors"], {"contact": MESSAGE})

    def test_core_has_no_forbidden_effects(self):
        source = inspect.getsource(core_module)
        tree = ast.parse(source)
        forbidden_calls = {"open", "eval", "exec", "compile", "getattr", "setattr", "__import__"}
        for node in ast.walk(tree):
            self.assertNotIsInstance(node, ast.ClassDef)
            self.assertNotIsInstance(node, ast.AsyncFunctionDef)
            self.assertNotIsInstance(node, ast.Await)
            self.assertNotIsInstance(node, ast.Yield)
            self.assertNotIsInstance(node, ast.YieldFrom)
            self.assertNotIsInstance(node, ast.Global)
            self.assertNotIsInstance(node, ast.Nonlocal)
            self.assertNotIsInstance(node, ast.Delete)
            self.assertNotIsInstance(node, ast.Import)
            self.assertNotIsInstance(node, ast.ImportFrom)
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = []
                if isinstance(node, ast.Assign):
                    targets = node.targets
                else:
                    targets = [node.target]
                for target in targets:
                    self.assertNotIsInstance(target, ast.Attribute)
            if isinstance(node, ast.FunctionDef):
                self.assertEqual(node.decorator_list, [])
                for default in node.args.defaults + node.args.kw_defaults:
                    if default is not None:
                        self.assertIsInstance(default, (ast.Constant, ast.Tuple, ast.NameConstant))
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name):
                    self.assertNotIn(func.id, forbidden_calls)
