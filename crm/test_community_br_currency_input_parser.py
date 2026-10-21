import unittest
from crm.features.br_currency_input_parser import run_feature


class BrCurrencyInputParserTest(unittest.TestCase):
    def test_non_object_payload_raises(self):
        for bad in [None, [], "raw", 123, 12.5, True]:
            with self.assertRaises(ValueError):
                run_feature(bad)

    def test_non_string_raw_raises_without_mutation(self):
        payload = {"raw": 123, "extra": 1}
        snapshot = {"raw": 123, "extra": 1}
        with self.assertRaises(ValueError):
            run_feature(payload)
        self.assertEqual(payload, snapshot)
        with self.assertRaises(ValueError):
            run_feature({})
        with self.assertRaises(ValueError):
            run_feature({"other": "x"})
        with self.assertRaises(ValueError):
            run_feature({"raw": None})
        with self.assertRaises(ValueError):
            run_feature({"raw": ["1"]})

    def test_extra_keys_ignored_and_no_mutation(self):
        payload = {"raw": "R$ 1.234,50", "foo": "bar"}
        result = run_feature(payload)
        self.assertEqual(payload, {"raw": "R$ 1.234,50", "foo": "bar"})
        self.assertEqual(result, {"cents": 123450, "value_csv": "1234.50", "value_display": "R$ 1234,50"})

    def test_r_prefix_grouped_value(self):
        result = run_feature({"raw": "R$ 1.234,50"})
        self.assertEqual(result["cents"], 123450)
        self.assertEqual(result["value_csv"], "1234.50")
        self.assertEqual(result["value_display"], "R$ 1234,50")
        self.assertEqual(run_feature({"raw": "R$1.234,50"}), result)
        self.assertEqual(run_feature({"raw": "  R$  1.234,50  "}), result)

    def test_plain_dot_and_zero(self):
        result = run_feature({"raw": "100.5"})
        self.assertEqual(result, {"cents": 10050, "value_csv": "100.50", "value_display": "R$ 100,50"})
        zero = run_feature({"raw": "0"})
        self.assertEqual(zero, {"cents": 0, "value_csv": "0.00", "value_display": "R$ 0,00"})
        self.assertEqual(run_feature({"raw": "0,00"}), zero)
        self.assertEqual(run_feature({"raw": "0.00"}), zero)
        self.assertEqual(run_feature({"raw": "R$ 0,00"}), zero)

    def test_comma_branch_rules(self):
        self.assertEqual(run_feature({"raw": "10,5"})["cents"], 1050)
        self.assertEqual(run_feature({"raw": "12.345,67"})["value_csv"], "12345.67")
        self.assertEqual(run_feature({"raw": "1.234.567,89"})["cents"], 123456789)
        for bad in ["1,2,3", "1,,2", "10,", "10,123", ",50", "12.34,50", "1.23,45", "1234.567,89", "1.2345,50", ".,50", "1.,50"]:
            with self.assertRaises(ValueError, msg=bad):
                run_feature({"raw": bad})

    def test_dot_only_branch_rules(self):
        self.assertEqual(run_feature({"raw": "100"})["cents"], 10000)
        self.assertEqual(run_feature({"raw": "100.50"})["cents"], 10050)
        self.assertEqual(run_feature({"raw": "0.5"})["cents"], 50)
        for bad in ["1.2.3", "1.000", "100.", ".5", "100.500", "10..5"]:
            with self.assertRaises(ValueError, msg=bad):
                run_feature({"raw": bad})

    def test_empty_whitespace_badchars_leadingzeros_oversize(self):
        for bad in ["", "   ", " \t\n\r ", "R$", "R$   "]:
            with self.assertRaises(ValueError, msg=repr(bad)):
                run_feature({"raw": bad})
        for bad in ["1 234", "1\t234", "1\n234", "R$ 1 234,50"]:
            with self.assertRaises(ValueError, msg=repr(bad)):
                run_feature({"raw": bad})
        for bad in ["12a", "10!", "$10", "r$ 10", "10$"]:
            with self.assertRaises(ValueError, msg=bad):
                run_feature({"raw": bad})
        for bad in ["00", "01", "00,50", "01,00", "00.50", "0.000,00"]:
            with self.assertRaises(ValueError, msg=bad):
                run_feature({"raw": bad})
        with self.assertRaises(ValueError):
            run_feature({"raw": "1234567890123"})
        with self.assertRaises(ValueError):
            run_feature({"raw": "9999999999999"})
        with self.assertRaises(ValueError):
            run_feature({"raw": "0" * 65})
        with self.assertRaises(ValueError):
            run_feature({"raw": "1" * 65})

    def test_max_value_boundary(self):
        result = run_feature({"raw": "999999999999,99"})
        self.assertEqual(result["cents"], 99999999999999)
        self.assertEqual(result["value_csv"], "999999999999.99")
        with self.assertRaises(ValueError):
            run_feature({"raw": "1000000000000,00"})
