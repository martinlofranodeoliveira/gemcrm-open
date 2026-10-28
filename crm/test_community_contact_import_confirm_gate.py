import copy
import unittest

from crm.features.contact_import_confirm_gate import run_feature

NONCE_A = "a" * 64
NONCE_B = "b" * 64
SESSION_C = "c" * 64
SESSION_D = "d" * 64


def base_payload():
    return {
        "presented_nonce_digest": NONCE_A,
        "canonical_nonce_digest": NONCE_A,
        "presented_session_digest": SESSION_C,
        "canonical_session_digest": SESSION_C,
        "canonical_ready": True,
        "canonical_expired": False,
        "receipt_exists": False,
        "session_has_csv": True,
    }


class ContactImportConfirmGateTests(unittest.TestCase):
    def test_allow_and_preserves_inputs(self):
        payload = base_payload()
        snapshot = copy.deepcopy(payload)
        result = run_feature(payload)
        self.assertEqual(result, {"decision": "allow", "can_import": True})
        self.assertTrue(result["can_import"])
        self.assertEqual(payload, snapshot)

    def test_missing_csv_returns_reupload_even_with_receipt(self):
        payload = base_payload()
        payload["session_has_csv"] = False
        payload["receipt_exists"] = True
        snapshot = copy.deepcopy(payload)
        result = run_feature(payload)
        self.assertEqual(result, {"decision": "reupload", "can_import": False})
        self.assertEqual(payload, snapshot)

    def test_session_mismatch(self):
        payload = base_payload()
        payload["presented_session_digest"] = SESSION_D
        result = run_feature(payload)
        self.assertEqual(result, {"decision": "session_mismatch", "can_import": False})

    def test_stale_preview(self):
        payload = base_payload()
        payload["presented_nonce_digest"] = NONCE_B
        result = run_feature(payload)
        self.assertEqual(result, {"decision": "stale_preview", "can_import": False})

    def test_expired(self):
        payload = base_payload()
        payload["canonical_expired"] = True
        result = run_feature(payload)
        self.assertEqual(result, {"decision": "expired", "can_import": False})

    def test_not_ready(self):
        payload = base_payload()
        payload["canonical_ready"] = False
        result = run_feature(payload)
        self.assertEqual(result, {"decision": "not_ready", "can_import": False})

    def test_replayed(self):
        payload = base_payload()
        payload["receipt_exists"] = True
        result = run_feature(payload)
        self.assertEqual(result, {"decision": "replayed", "can_import": False})

    def test_precedence_reupload_first(self):
        payload = base_payload()
        payload["session_has_csv"] = False
        payload["presented_session_digest"] = SESSION_D
        payload["presented_nonce_digest"] = NONCE_B
        payload["canonical_expired"] = True
        payload["canonical_ready"] = False
        payload["receipt_exists"] = True
        result = run_feature(payload)
        self.assertEqual(result["decision"], "reupload")

    def test_precedence_session_before_stale_expired_ready_replayed(self):
        payload = base_payload()
        payload["presented_session_digest"] = SESSION_D
        payload["presented_nonce_digest"] = NONCE_B
        payload["canonical_expired"] = True
        payload["canonical_ready"] = False
        payload["receipt_exists"] = True
        self.assertEqual(run_feature(payload)["decision"], "session_mismatch")
        payload2 = base_payload()
        payload2["presented_nonce_digest"] = NONCE_B
        payload2["canonical_expired"] = True
        payload2["canonical_ready"] = False
        payload2["receipt_exists"] = True
        self.assertEqual(run_feature(payload2)["decision"], "stale_preview")
        payload3 = base_payload()
        payload3["canonical_expired"] = True
        payload3["canonical_ready"] = False
        payload3["receipt_exists"] = True
        self.assertEqual(run_feature(payload3)["decision"], "expired")
        payload4 = base_payload()
        payload4["canonical_ready"] = False
        payload4["receipt_exists"] = True
        self.assertEqual(run_feature(payload4)["decision"], "not_ready")

    def test_malformed_non_dict(self):
        for bad in (None, [], "x", 42, True):
            with self.assertRaises(ValueError):
                run_feature(bad)

    def test_malformed_missing_keys(self):
        for key in list(base_payload().keys()):
            payload = base_payload()
            del payload[key]
            snapshot = copy.deepcopy(payload)
            with self.assertRaises(ValueError):
                run_feature(payload)
            self.assertEqual(payload, snapshot)

    def test_malformed_non_bool_flags(self):
        for key in ("canonical_ready", "canonical_expired", "receipt_exists", "session_has_csv"):
            for bad in (0, 1, "true", None, []):
                payload = base_payload()
                payload[key] = bad
                with self.assertRaises(ValueError):
                    run_feature(payload)

    def test_malformed_bad_digests(self):
        for key in ("presented_nonce_digest", "canonical_nonce_digest", "presented_session_digest", "canonical_session_digest"):
            for bad in (None, 123, "", "a" * 63, "a" * 65, "A" * 64, "g" * 64, "a" * 63 + " ", ["a" * 64]):
                payload = base_payload()
                payload[key] = bad
                with self.assertRaises(ValueError):
                    run_feature(payload)

    def test_extra_keys_ignored_and_deterministic(self):
        payload = base_payload()
        payload["extra"] = "ignored"
        snapshot = copy.deepcopy(payload)
        first = run_feature(payload)
        second = run_feature(payload)
        self.assertEqual(first, {"decision": "allow", "can_import": True})
        self.assertEqual(first, second)
        self.assertIsNot(first, second)
        self.assertEqual(payload, snapshot)

    def test_malformed_has_no_side_effects(self):
        payload = base_payload()
        payload["canonical_ready"] = "yes"
        snapshot = copy.deepcopy(payload)
        with self.assertRaises(ValueError):
            run_feature(payload)
        self.assertEqual(payload, snapshot)
