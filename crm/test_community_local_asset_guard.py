import unittest
from crm.features.local_asset_guard import run_feature


class LocalAssetGuardTests(unittest.TestCase):
    def test_missing_assets_defaults_empty(self):
        result = run_feature({})
        self.assertEqual(result, {"total": 0, "external_count": 0, "local_count": 0, "allows_offline": True, "external": [], "local": []})

    def test_extra_keys_ignored(self):
        result = run_feature({"assets": [], "other": 123, "x": "y"})
        self.assertEqual(result["total"], 0)
        self.assertTrue(result["allows_offline"])

    def test_none_payload_raises(self):
        with self.assertRaises(ValueError):
            run_feature(None)

    def test_non_dict_payload_raises(self):
        for bad in ([], "x", 1, 1.5, True, ()): 
            with self.assertRaises(ValueError):
                run_feature(bad)

    def test_none_assets_raises(self):
        with self.assertRaises(ValueError):
            run_feature({"assets": None})

    def test_non_list_assets_raises(self):
        for bad in ("x", "http://a", 1, {}, (), True):
            with self.assertRaises(ValueError):
                run_feature({"assets": bad})

    def test_too_many_assets_raises(self):
        with self.assertRaises(ValueError):
            run_feature({"assets": ["/a"] * 51})
        result = run_feature({"assets": ["/a"] * 50})
        self.assertEqual(result["total"], 50)

    def test_non_string_entry_raises(self):
        for bad in (1, None, True, 1.5, [], {}, b"/a"):
            with self.assertRaises(ValueError):
                run_feature({"assets": [bad]})

    def test_empty_entry_raises(self):
        with self.assertRaises(ValueError):
            run_feature({"assets": [""]})

    def test_whitespace_only_raises(self):
        for bad in ("   ", "\t\n ", " \t "):
            with self.assertRaises(ValueError):
                run_feature({"assets": [bad]})

    def test_too_long_entry_raises(self):
        with self.assertRaises(ValueError):
            run_feature({"assets": ["a" * 1001]})
        result = run_feature({"assets": ["a" * 1000]})
        self.assertEqual(result["total"], 1)

    def test_basic_mixed_example(self):
        result = run_feature({"assets": ["/static/crm/app.css", "https://cdn.example.com/lib.js"]})
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["external_count"], 1)
        self.assertEqual(result["local_count"], 1)
        self.assertFalse(result["allows_offline"])
        self.assertEqual(result["external"], ["https://cdn.example.com/lib.js"])
        self.assertEqual(result["local"], ["/static/crm/app.css"])

    def test_trim_casefold_and_order_with_duplicates(self):
        result = run_feature({"assets": ["//cdn.example.com/x.js", "  HTTP://example.com/y.js ", "/static/crm/app.css", "data:text/css,body{}"]})
        self.assertEqual(result["external"], ["//cdn.example.com/x.js", "HTTP://example.com/y.js"])
        self.assertEqual(result["local"], ["/static/crm/app.css", "data:text/css,body{}"])
        self.assertEqual(result["total"], 4)
        self.assertEqual(result["external_count"], 2)
        self.assertEqual(result["local_count"], 2)
        self.assertFalse(result["allows_offline"])

    def test_preserves_inner_case(self):
        result = run_feature({"assets": ["  HTTPS://Example.COM/Path/ABC.JS  "]})
        self.assertEqual(result["external"], ["HTTPS://Example.COM/Path/ABC.JS"])

    def test_duplicates_in_order(self):
        result = run_feature({"assets": ["/a.css", "https://x/y.js", "/a.css", "https://x/y.js"]})
        self.assertEqual(result["local"], ["/a.css", "/a.css"])
        self.assertEqual(result["external"], ["https://x/y.js", "https://x/y.js"])
        self.assertEqual(result["total"], 4)

    def test_local_kinds(self):
        assets = ["/static/crm/app.css", "app.css", "./rel.js", "../up.js", "data:text/css,body{}", "blob:https://x/1", "HTTPSX://example.com/y.js", "httpx://y"]
        result = run_feature({"assets": assets})
        self.assertEqual(result["external_count"], 0)
        self.assertEqual(result["local_count"], 8)
        self.assertTrue(result["allows_offline"])
        self.assertEqual(result["local"], assets)

    def test_protocol_relative_is_external(self):
        result = run_feature({"assets": ["//cdn.example.com/a.js"]})
        self.assertEqual(result["external_count"], 1)
        self.assertFalse(result["allows_offline"])

    def test_does_not_mutate_inputs(self):
        payload = {"assets": ["  /a.css ", "https://x/y.js"]}
        before = {"assets": ["  /a.css ", "https://x/y.js"]}
        result = run_feature(payload)
        self.assertEqual(payload, before)
        self.assertEqual(payload["assets"], ["  /a.css ", "https://x/y.js"])
        self.assertEqual(result["local"], ["/a.css"])

    def test_deterministic(self):
        payload = {"assets": ["/b.css", "http://e.com/a.js"]}
        first = run_feature(payload)
        second = run_feature(payload)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
