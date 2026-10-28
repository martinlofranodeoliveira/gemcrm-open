import copy
import unittest

from crm.features.contact_import_batch_guard import run_feature


class ContactImportBatchGuardTest(unittest.TestCase):
    def test_small_batch_allowed(self):
        payload = {"file_bytes": 1024, "preview_rows": 2, "existing_contacts": 10, "matching_companies": 5}
        snapshot = copy.deepcopy(payload)
        result = run_feature(payload)
        self.assertEqual(payload, snapshot)
        self.assertTrue(result["allowed"])
        self.assertEqual(result["reasons"], [])
        self.assertEqual(result["file_bytes"], 1024)
        self.assertEqual(result["preview_rows"], 2)
        self.assertEqual(result["existing_contacts"], 10)
        self.assertEqual(result["matching_companies"], 5)
        self.assertEqual(result["limits"], {"max_file_bytes": 262144, "max_preview_rows": 500, "max_existing_contacts": 20000, "max_matching_companies": 20000})

    def test_exact_ceiling_allowed(self):
        payload = {"file_bytes": 262144, "preview_rows": 500, "existing_contacts": 20000, "matching_companies": 20000}
        result = run_feature(payload)
        self.assertTrue(result["allowed"])
        self.assertEqual(result["reasons"], [])

    def test_extra_keys_ignored(self):
        payload = {"file_bytes": 10, "preview_rows": 1, "existing_contacts": 0, "matching_companies": 0, "owner": "x", "other": 99}
        result = run_feature(payload)
        self.assertTrue(result["allowed"])
        self.assertEqual(result["reasons"], [])
        self.assertEqual(result["file_bytes"], 10)

    def test_file_too_large(self):
        payload = {"file_bytes": 262145, "preview_rows": 1, "existing_contacts": 0, "matching_companies": 1}
        snapshot = copy.deepcopy(payload)
        result = run_feature(payload)
        self.assertEqual(payload, snapshot)
        self.assertFalse(result["allowed"])
        self.assertEqual(result["reasons"], ["file_too_large"])
        self.assertEqual(result["file_bytes"], 262145)
        self.assertEqual(result["preview_rows"], 1)
        self.assertEqual(result["existing_contacts"], 0)
        self.assertEqual(result["matching_companies"], 1)

    def test_too_many_rows(self):
        payload = {"file_bytes": 100, "preview_rows": 501, "existing_contacts": 3, "matching_companies": 4}
        result = run_feature(payload)
        self.assertFalse(result["allowed"])
        self.assertEqual(result["reasons"], ["too_many_rows"])
        self.assertEqual(result["file_bytes"], 100)
        self.assertEqual(result["existing_contacts"], 3)

    def test_too_many_existing_contacts(self):
        payload = {"file_bytes": 100, "preview_rows": 10, "existing_contacts": 20001, "matching_companies": 5}
        result = run_feature(payload)
        self.assertFalse(result["allowed"])
        self.assertEqual(result["reasons"], ["too_many_existing_contacts"])

    def test_too_many_matching_companies(self):
        payload = {"file_bytes": 100, "preview_rows": 10, "existing_contacts": 5, "matching_companies": 20001}
        result = run_feature(payload)
        self.assertFalse(result["allowed"])
        self.assertEqual(result["reasons"], ["too_many_matching_companies"])

    def test_combined_reasons_order(self):
        payload = {"file_bytes": 100, "preview_rows": 0, "existing_contacts": 20001, "matching_companies": 20001}
        result = run_feature(payload)
        self.assertFalse(result["allowed"])
        self.assertEqual(result["reasons"], ["empty_preview", "too_many_existing_contacts", "too_many_matching_companies"])

    def test_zero_file_bytes(self):
        payload = {"file_bytes": 0, "preview_rows": 1, "existing_contacts": 0, "matching_companies": 0}
        result = run_feature(payload)
        self.assertFalse(result["allowed"])
        self.assertEqual(result["reasons"], ["empty_file"])

    def test_zero_preview_rows(self):
        payload = {"file_bytes": 10, "preview_rows": 0, "existing_contacts": 0, "matching_companies": 0}
        result = run_feature(payload)
        self.assertFalse(result["allowed"])
        self.assertEqual(result["reasons"], ["empty_preview"])

    def test_zero_both(self):
        payload = {"file_bytes": 0, "preview_rows": 0, "existing_contacts": 0, "matching_companies": 0}
        result = run_feature(payload)
        self.assertFalse(result["allowed"])
        self.assertEqual(result["reasons"], ["empty_file", "empty_preview"])

    def test_missing_keys_raise(self):
        base = {"file_bytes": 10, "preview_rows": 1, "existing_contacts": 0, "matching_companies": 0}
        for key in ["file_bytes", "preview_rows", "existing_contacts", "matching_companies"]:
            payload = {k: v for k, v in base.items() if k != key}
            snapshot = copy.deepcopy(payload)
            with self.assertRaises(ValueError):
                run_feature(payload)
            self.assertEqual(payload, snapshot)

    def test_none_and_non_dict_raise(self):
        with self.assertRaises(ValueError):
            run_feature(None)
        for bad in [[], "x", 123, 1.5, True, False, (1, 2)]:
            with self.assertRaises(ValueError):
                run_feature(bad)

    def test_bool_float_string_raise_without_mutation(self):
        bad_values = [True, False, 1.5, "10", None, [10], {"n": 1}]
        for bad in bad_values:
            for key in ["file_bytes", "preview_rows", "existing_contacts", "matching_companies"]:
                payload = {"file_bytes": 10, "preview_rows": 1, "existing_contacts": 0, "matching_companies": 0}
                payload[key] = bad
                snapshot = copy.deepcopy(payload)
                with self.assertRaises(ValueError):
                    run_feature(payload)
                self.assertEqual(payload, snapshot)

    def test_negative_raise_without_mutation(self):
        for key in ["file_bytes", "preview_rows", "existing_contacts", "matching_companies"]:
            payload = {"file_bytes": 10, "preview_rows": 1, "existing_contacts": 0, "matching_companies": 0}
            payload[key] = -1
            snapshot = copy.deepcopy(payload)
            with self.assertRaises(ValueError):
                run_feature(payload)
            self.assertEqual(payload, snapshot)

    def test_none_value_raise(self):
        payload = {"file_bytes": None, "preview_rows": 1, "existing_contacts": 0, "matching_companies": 0}
        snapshot = copy.deepcopy(payload)
        with self.assertRaises(ValueError):
            run_feature(payload)
        self.assertEqual(payload, snapshot)


if __name__ == "__main__":
    unittest.main()
