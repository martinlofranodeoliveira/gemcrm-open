"""Independent public tests for spreadsheet-safe CSV cell guard core."""
import unittest

from crm.features.csv_cell_guard import run_feature


class CsvCellGuardTest(unittest.TestCase):
    def test_missing_cells_returns_empty(self):
        out = run_feature({})
        self.assertEqual(out, {"total_count": 0, "flagged_count": 0, "results": []})

    def test_extra_keys_ignored(self):
        out = run_feature({"other": 123})
        self.assertEqual(out["total_count"], 0)
        self.assertEqual(out["flagged_count"], 0)
        self.assertEqual(out["results"], [])

    def test_empty_list_returns_empty(self):
        out = run_feature({"cells": []})
        self.assertEqual(out["total_count"], 0)
        self.assertEqual(out["flagged_count"], 0)
        self.assertEqual(out["results"], [])

    def test_safe_text_unchanged(self):
        out = run_feature({"cells": ["hello", "normal, value", "123", "hello=world"]})
        self.assertEqual(out["total_count"], 4)
        self.assertEqual(out["flagged_count"], 0)
        for i in range(4):
            self.assertFalse(out["results"][i]["flagged"])
            self.assertEqual(out["results"][i]["index"], i)
        self.assertEqual(out["results"][0]["safe"], "hello")
        self.assertEqual(out["results"][1]["safe"], "normal, value")

    def test_empty_and_whitespace_only_safe(self):
        cells = ["", "   ", "\t\r\n ", "  \t"]
        out = run_feature({"cells": cells})
        self.assertEqual(out["total_count"], 4)
        self.assertEqual(out["flagged_count"], 0)
        for i in range(4):
            self.assertFalse(out["results"][i]["flagged"])
            self.assertEqual(out["results"][i]["safe"], cells[i])
            self.assertEqual(out["results"][i]["source"], cells[i])

    def test_all_triggers_flagged(self):
        cells = ["=1", "+1", "-1", "@1", "|1", "%1"]
        out = run_feature({"cells": cells})
        self.assertEqual(out["total_count"], 6)
        self.assertEqual(out["flagged_count"], 6)
        for i in range(6):
            self.assertTrue(out["results"][i]["flagged"])
            self.assertEqual(out["results"][i]["safe"], "'" + cells[i])
            self.assertEqual(out["results"][i]["source"], cells[i])
            self.assertEqual(out["results"][i]["index"], i)

    def test_leading_whitespace_preserved(self):
        cells = [" @test", "  +calc", "\t=SUM(A1)", "\r\n-5", " \t\r\n%v"]
        out = run_feature({"cells": cells})
        self.assertEqual(out["flagged_count"], 5)
        for i in range(5):
            self.assertTrue(out["results"][i]["flagged"])
            self.assertEqual(out["results"][i]["safe"], "'" + cells[i])
            self.assertEqual(out["results"][i]["source"], cells[i])

    def test_only_space_tab_cr_lf_stripped(self):
        out = run_feature({"cells": ["\u00a0=foo"]})
        self.assertFalse(out["results"][0]["flagged"])
        self.assertEqual(out["results"][0]["safe"], "\u00a0=foo")
        out2 = run_feature({"cells": [";cmd", "'=x", "#tag"]})
        self.assertEqual(out2["flagged_count"], 0)

    def test_contract_example_one(self):
        out = run_feature({"cells": ["hello", "=SUM(A1)", " @test"]})
        self.assertEqual(out["total_count"], 3)
        self.assertEqual(out["flagged_count"], 2)
        self.assertEqual(out["results"][0], {"index": 0, "source": "hello", "safe": "hello", "flagged": False})
        self.assertEqual(out["results"][1], {"index": 1, "source": "=SUM(A1)", "safe": "'=SUM(A1)", "flagged": True})
        self.assertEqual(out["results"][2], {"index": 2, "source": " @test", "safe": "' @test", "flagged": True})

    def test_contract_example_two(self):
        out = run_feature({"cells": ["-5", "  +calc", "normal, value"]})
        self.assertEqual(out["total_count"], 3)
        self.assertEqual(out["flagged_count"], 2)
        self.assertEqual(out["results"][0]["safe"], "'-5")
        self.assertEqual(out["results"][1]["safe"], "'  +calc")
        self.assertEqual(out["results"][2]["safe"], "normal, value")

    def test_malformed_payload_raises(self):
        for bad in [None, [], "x", 123, True]:
            with self.assertRaises(ValueError):
                run_feature(bad)

    def test_non_list_cells_raises(self):
        for bad in [None, {}, "x", 123, ("a",)]:
            with self.assertRaises(ValueError):
                run_feature({"cells": bad})

    def test_too_many_cells_raises(self):
        with self.assertRaises(ValueError):
            run_feature({"cells": ["a"] * 2001})

    def test_non_string_cell_raises(self):
        for bad_cells in [[1], [["a"]], [[None]], [["ok", 2]], [[b"x"]], [[True]]]:
            with self.assertRaises(ValueError):
                run_feature({"cells": bad_cells})

    def test_too_long_cell_raises(self):
        with self.assertRaises(ValueError):
            run_feature({"cells": ["x" * 5001]})

    def test_boundary_limits_pass(self):
        out = run_feature({"cells": ["x" * 5000]})
        self.assertEqual(out["total_count"], 1)
        self.assertEqual(out["results"][0]["safe"], "x" * 5000)
        out2 = run_feature({"cells": ["a"] * 2000})
        self.assertEqual(out2["total_count"], 2000)
        self.assertEqual(out2["flagged_count"], 0)

    def test_inputs_never_mutated_and_order(self):
        cells = ["b", "=a", "c", "  @x", ""]
        payload = {"cells": cells, "extra": "keep"}
        snapshot_cells = cells[:]
        snapshot_payload_keys = [k for k in payload]
        out = run_feature(payload)
        self.assertEqual(cells, snapshot_cells)
        self.assertEqual([k for k in payload], snapshot_payload_keys)
        self.assertEqual(payload["cells"], snapshot_cells)
        self.assertEqual([r["index"] for r in out["results"]], [0, 1, 2, 3, 4])
        self.assertEqual([r["source"] for r in out["results"]], snapshot_cells)
        self.assertEqual(out["total_count"], 5)
        self.assertEqual(out["flagged_count"], 2)
        self.assertTrue(out["results"][1]["flagged"])
        self.assertTrue(out["results"][3]["flagged"])


if __name__ == "__main__":
    unittest.main()
