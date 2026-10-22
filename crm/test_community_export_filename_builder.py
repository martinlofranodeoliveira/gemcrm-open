import copy
import unittest

from crm.features.export_filename_builder import run_feature


class ExportFilenameBuilderCommunityTest(unittest.TestCase):
    def test_contatos_sao_marina(self):
        payload = {"base": "Contatos", "tag": "S\u00e3o Marina"}
        snapshot = copy.deepcopy(payload)
        result = run_feature(payload)
        self.assertEqual(result["base_slug"], "contatos")
        self.assertEqual(result["tag_slug"], "sao-marina")
        self.assertEqual(result["filename"], "contatos-sao-marina.csv")
        self.assertEqual(result["ext"], "csv")
        self.assertEqual(payload, snapshot)

    def test_empty_payload(self):
        result = run_feature({})
        self.assertEqual(result["base_slug"], "export")
        self.assertEqual(result["tag_slug"], "")
        self.assertEqual(result["filename"], "export.csv")
        self.assertEqual(result["ext"], "csv")

    def test_pipeline_date_range(self):
        payload = {"base": "Pipeline", "tag": "2026-01-01 a 2026-01-31"}
        result = run_feature(payload)
        self.assertEqual(result["base_slug"], "pipeline")
        self.assertEqual(result["tag_slug"], "2026-01-01-a-2026-01-31")
        self.assertEqual(result["filename"], "pipeline-2026-01-01-a-2026-01-31.csv")
        self.assertEqual(result["ext"], "csv")

    def test_accents_case_symbol_collapse(self):
        result = run_feature({"base": "  CONTATOS!!!", "tag": "S\u00e3o---Marina__Teste"})
        self.assertEqual(result["base_slug"], "contatos")
        self.assertEqual(result["tag_slug"], "sao-marina-teste")
        self.assertEqual(result["filename"], "contatos-sao-marina-teste.csv")
        trimmed = run_feature({"base": "---Ol\u00e1 Mundo---", "tag": "---Oi---"})
        self.assertEqual(trimmed["base_slug"], "ola-mundo")
        self.assertEqual(trimmed["tag_slug"], "oi")

    def test_whitespace_none_extras_and_fallbacks(self):
        result = run_feature({"base": "   \t\n\r  ", "tag": "  \t  ", "ext": None, "other": 123})
        self.assertEqual(result["base_slug"], "export")
        self.assertEqual(result["tag_slug"], "")
        self.assertEqual(result["filename"], "export.csv")
        none_result = run_feature({"base": None, "tag": None, "ext": None})
        self.assertEqual(none_result["filename"], "export.csv")
        symbols = run_feature({"base": "!!!", "tag": "!!!"})
        self.assertEqual(symbols["base_slug"], "export")
        self.assertEqual(symbols["tag_slug"], "")
        self.assertEqual(symbols["filename"], "export.csv")
        upper_ext = run_feature({"base": "Contatos", "ext": "  CSV  "})
        self.assertEqual(upper_ext["ext"], "csv")
        self.assertEqual(upper_ext["filename"], "contatos.csv")

    def test_truncation_limits(self):
        long_base = "a" * 50
        long_tag = "b" * 50
        result = run_feature({"base": long_base, "tag": long_tag})
        self.assertEqual(result["base_slug"], "a" * 30)
        self.assertEqual(result["tag_slug"], "b" * 40)
        self.assertEqual(result["filename"], "a" * 30 + "-" + "b" * 40 + ".csv")
        boundary_base = "a" * 29 + " " + "b" * 10
        boundary = run_feature({"base": boundary_base})
        self.assertEqual(boundary["base_slug"], "a" * 29)
        boundary_tag = "c" * 39 + " " + "d" * 10
        boundary2 = run_feature({"base": "x", "tag": boundary_tag})
        self.assertEqual(boundary2["tag_slug"], "c" * 39)

    def test_errors_without_mutation(self):
        for bad in (None, [], "x", 123, (("base", "x"),)):
            payload = bad
            before = copy.deepcopy(payload)
            with self.assertRaises(ValueError):
                run_feature(payload)
            self.assertEqual(copy.deepcopy(payload), before)
        oversized = "x" * 501
        for payload in ({"base": oversized}, {"tag": oversized}):
            snapshot = copy.deepcopy(payload)
            with self.assertRaises(ValueError):
                run_feature(payload)
            self.assertEqual(payload, snapshot)
        for payload in ({"base": 123}, {"base": True}, {"tag": 45}, {"ext": 123}):
            snapshot = copy.deepcopy(payload)
            with self.assertRaises(ValueError):
                run_feature(payload)
            self.assertEqual(payload, snapshot)
        for bad_ext in ("txt", "pdf", "", "csvv", "csv2"):
            payload = {"base": "Contatos", "ext": bad_ext}
            snapshot = copy.deepcopy(payload)
            with self.assertRaises(ValueError):
                run_feature(payload)
            self.assertEqual(payload, snapshot)

    def test_deterministic_and_ignores_extras(self):
        payload = {"base": "Contatos", "tag": "S\u00e3o Marina", "extra": [1, 2]} 
        first = run_feature(payload)
        second = run_feature({"base": "Contatos", "tag": "S\u00e3o Marina"})
        self.assertEqual(first, second)
