import unittest
from crm.features.company_website_link_guard import run_feature


class CompanyWebsiteLinkGuardTest(unittest.TestCase):
    def test_empty_payload_defaults(self):
        out = run_feature({})
        self.assertEqual(out, {"total_count": 0, "allowed_count": 0, "blocked_count": 0, "results": []})

    def test_extra_keys_ignored(self):
        out = run_feature({"websites": [], "other": 1})
        self.assertEqual(out["total_count"], 0)
        self.assertEqual(out["results"], [])

    def test_example_one(self):
        out = run_feature({"websites": ["", "https://www.exemplo.com.br", "javascript:alert(1)"]})
        self.assertEqual(out["total_count"], 3)
        self.assertEqual(out["allowed_count"], 2)
        self.assertEqual(out["blocked_count"], 1)
        self.assertEqual(out["results"][0]["kind"], "blank")
        self.assertTrue(out["results"][0]["allowed"])
        self.assertIsNone(out["results"][0]["href"])
        self.assertEqual(out["results"][0]["display_host"], "")
        self.assertEqual(out["results"][0]["reasons"], [])
        self.assertEqual(out["results"][1]["href"], "https://www.exemplo.com.br")
        self.assertEqual(out["results"][1]["display_host"], "www.exemplo.com.br")
        self.assertEqual(out["results"][2]["reasons"], ["unsafe_scheme"])
        self.assertFalse(out["results"][2]["allowed"])
        self.assertIsNone(out["results"][2]["href"])

    def test_example_two_trim_and_host(self):
        out = run_feature({"websites": ["  https://Loja.Exemplo.com/caminho  ", "https://exemplo.com/a<b", "https://"]})
        self.assertEqual(out["allowed_count"], 1)
        self.assertEqual(out["blocked_count"], 2)
        first = out["results"][0]
        self.assertEqual(first["trimmed"], "https://Loja.Exemplo.com/caminho")
        self.assertEqual(first["href"], "https://Loja.Exemplo.com/caminho")
        self.assertEqual(first["display_host"], "loja.exemplo.com")
        self.assertTrue(first["allowed"])
        self.assertEqual(out["results"][1]["reasons"], ["unsafe_chars"])
        self.assertEqual(out["results"][2]["reasons"], ["missing_host"])

    def test_blank_whitespace_only(self):
        out = run_feature({"websites": ["   \t\n\r  "]})
        r = out["results"][0]
        self.assertEqual(r["trimmed"], "")
        self.assertEqual(r["kind"], "blank")
        self.assertTrue(r["allowed"])
        self.assertIsNone(r["href"])
        self.assertEqual(r["display_host"], "")
        self.assertEqual(r["reasons"], [])

    def test_scheme_case_insensitive(self):
        out = run_feature({"websites": ["HTTP://example.com", "HtTpS://Example.COM/Path"]})
        self.assertEqual(out["allowed_count"], 2)
        self.assertEqual(out["results"][0]["display_host"], "example.com")
        self.assertEqual(out["results"][1]["display_host"], "example.com")

    def test_unsafe_scheme_blocked(self):
        out = run_feature({"websites": ["ftp://example.com", "data:text/plain,hi", "example.com"]})
        for r in out["results"]:
            self.assertFalse(r["allowed"])
            self.assertIsNone(r["href"])
            self.assertEqual(r["display_host"], "")
            self.assertIn("unsafe_scheme", r["reasons"])

    def test_contains_space(self):
        out = run_feature({"websites": ["https://example.com/a b"]})
        r = out["results"][0]
        self.assertFalse(r["allowed"])
        self.assertIn("contains_space", r["reasons"])
        self.assertIsNone(r["href"])

    def test_unsafe_chars_each(self):
        for ch in ["<", ">", '"', "'", "`", "\\"]:
            out = run_feature({"websites": ["https://example.com/a" + ch]})
            self.assertIn("unsafe_chars", out["results"][0]["reasons"], msg=ch)

    def test_missing_host_empty(self):
        for w in ["https://", "http://", "https:///path", "https://?x=1", "https://#f"]:
            out = run_feature({"websites": [w]})
            self.assertIn("missing_host", out["results"][0]["reasons"], msg=w)

    def test_host_cut_at_slash_query_hash(self):
        out = run_feature({"websites": ["https://Example.COM:8080/p?q=1#f"]})
        self.assertEqual(out["results"][0]["display_host"], "example.com:8080")

    def test_fixed_order_multiple_reasons(self):
        out = run_feature({"websites": ["ftp://exa mple.com/a<b"]})
        self.assertEqual(out["results"][0]["reasons"], ["unsafe_scheme", "contains_space", "unsafe_chars"])
        out2 = run_feature({"websites": ["https://exa<mple.com"]})
        self.assertEqual(out2["results"][0]["reasons"], ["unsafe_chars", "missing_host"])

    def test_preserves_order_and_counts(self):
        websites = ["https://a.com", "", "javascript:alert(1)"]
        snapshot = list(websites)
        out = run_feature({"websites": websites})
        self.assertEqual([r["index"] for r in out["results"]], [0, 1, 2])
        self.assertEqual([r["website"] for r in out["results"]], snapshot)
        self.assertEqual(websites, snapshot)
        self.assertEqual(out["total_count"], 3)
        self.assertEqual(out["allowed_count"], 2)
        self.assertEqual(out["blocked_count"], 1)

    def test_does_not_mutate_payload(self):
        payload = {"websites": ["  https://example.com  "]}
        before = {"websites": ["  https://example.com  "]}
        run_feature(payload)
        self.assertEqual(payload, before)

    def test_validation_errors(self):
        with self.assertRaises(ValueError):
            run_feature(None)
        with self.assertRaises(ValueError):
            run_feature("x")
        with self.assertRaises(ValueError):
            run_feature([])
        with self.assertRaises(ValueError):
            run_feature({"websites": None})
        with self.assertRaises(ValueError):
            run_feature({"websites": "https://a.com"})
        with self.assertRaises(ValueError):
            run_feature({"websites": ["https://a.com"] * 21})
        with self.assertRaises(ValueError):
            run_feature({"websites": [123]})
        with self.assertRaises(ValueError):
            run_feature({"websites": [None]})
        with self.assertRaises(ValueError):
            run_feature({"websites": ["x" * 501]})

    def test_deterministic(self):
        payload = {"websites": ["https://example.com", ""]}
        self.assertEqual(run_feature(payload), run_feature(payload))


if __name__ == "__main__":
    unittest.main()
