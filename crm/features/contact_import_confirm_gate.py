# Contact import confirm gate core.
# Pure deterministic helper; caller owns account filtering, clock and storage.
DECISION_ALLOW = "allow"
DECISION_REUPLOAD = "reupload"
DECISION_SESSION_MISMATCH = "session_mismatch"
DECISION_STALE_PREVIEW = "stale_preview"
DECISION_EXPIRED = "expired"
DECISION_NOT_READY = "not_ready"
DECISION_REPLAYED = "replayed"
HEX_DIGITS = "0123456789abcdef"


def _is_hex_digest(value):
    if not isinstance(value, str):
        return False
    if len(value) != 64:
        return False
    for ch in value:
        if ch not in HEX_DIGITS:
            return False
    return True


def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    if "presented_nonce_digest" not in payload:
        raise ValueError("missing presented_nonce_digest")
    if "canonical_nonce_digest" not in payload:
        raise ValueError("missing canonical_nonce_digest")
    if "presented_session_digest" not in payload:
        raise ValueError("missing presented_session_digest")
    if "canonical_session_digest" not in payload:
        raise ValueError("missing canonical_session_digest")
    if "canonical_ready" not in payload:
        raise ValueError("missing canonical_ready")
    if "canonical_expired" not in payload:
        raise ValueError("missing canonical_expired")
    if "receipt_exists" not in payload:
        raise ValueError("missing receipt_exists")
    if "session_has_csv" not in payload:
        raise ValueError("missing session_has_csv")
    presented_nonce_digest = payload["presented_nonce_digest"]
    canonical_nonce_digest = payload["canonical_nonce_digest"]
    presented_session_digest = payload["presented_session_digest"]
    canonical_session_digest = payload["canonical_session_digest"]
    canonical_ready = payload["canonical_ready"]
    canonical_expired = payload["canonical_expired"]
    receipt_exists = payload["receipt_exists"]
    session_has_csv = payload["session_has_csv"]
    if not _is_hex_digest(presented_nonce_digest):
        raise ValueError("invalid presented_nonce_digest")
    if not _is_hex_digest(canonical_nonce_digest):
        raise ValueError("invalid canonical_nonce_digest")
    if not _is_hex_digest(presented_session_digest):
        raise ValueError("invalid presented_session_digest")
    if not _is_hex_digest(canonical_session_digest):
        raise ValueError("invalid canonical_session_digest")
    if type(canonical_ready) is not bool:
        raise ValueError("invalid canonical_ready")
    if type(canonical_expired) is not bool:
        raise ValueError("invalid canonical_expired")
    if type(receipt_exists) is not bool:
        raise ValueError("invalid receipt_exists")
    if type(session_has_csv) is not bool:
        raise ValueError("invalid session_has_csv")
    if session_has_csv is False:
        return {"decision": DECISION_REUPLOAD, "can_import": False}
    if presented_session_digest != canonical_session_digest:
        return {"decision": DECISION_SESSION_MISMATCH, "can_import": False}
    if presented_nonce_digest != canonical_nonce_digest:
        return {"decision": DECISION_STALE_PREVIEW, "can_import": False}
    if canonical_expired is True:
        return {"decision": DECISION_EXPIRED, "can_import": False}
    if canonical_ready is False:
        return {"decision": DECISION_NOT_READY, "can_import": False}
    if receipt_exists is True:
        return {"decision": DECISION_REPLAYED, "can_import": False}
    return {"decision": DECISION_ALLOW, "can_import": True}
