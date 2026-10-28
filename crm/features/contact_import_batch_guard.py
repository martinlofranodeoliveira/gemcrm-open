MAX_FILE_BYTES = 262144
MAX_PREVIEW_ROWS = 500
MAX_EXISTING_CONTACTS = 20000
MAX_MATCHING_COMPANIES = 20000


def _require_count(payload, key):
    if key not in payload:
        raise ValueError(key)
    value = payload[key]
    if type(value) is bool:
        raise ValueError(key)
    if type(value) is not int:
        raise ValueError(key)
    if value < 0:
        raise ValueError(key)
    return value


def run_feature(payload):
    if type(payload) is not dict:
        raise ValueError("payload")
    file_bytes = _require_count(payload, "file_bytes")
    preview_rows = _require_count(payload, "preview_rows")
    existing_contacts = _require_count(payload, "existing_contacts")
    matching_companies = _require_count(payload, "matching_companies")
    reasons = []
    if file_bytes == 0:
        reasons.append("empty_file")
    else:
        if file_bytes > MAX_FILE_BYTES:
            reasons.append("file_too_large")
    if preview_rows == 0:
        reasons.append("empty_preview")
    else:
        if preview_rows > MAX_PREVIEW_ROWS:
            reasons.append("too_many_rows")
    if existing_contacts > MAX_EXISTING_CONTACTS:
        reasons.append("too_many_existing_contacts")
    if matching_companies > MAX_MATCHING_COMPANIES:
        reasons.append("too_many_matching_companies")
    if len(reasons) == 0:
        allowed = True
    else:
        allowed = False
    limits = {"max_file_bytes": MAX_FILE_BYTES, "max_preview_rows": MAX_PREVIEW_ROWS, "max_existing_contacts": MAX_EXISTING_CONTACTS, "max_matching_companies": MAX_MATCHING_COMPANIES}
    result = {"file_bytes": file_bytes, "preview_rows": preview_rows, "existing_contacts": existing_contacts, "matching_companies": matching_companies, "allowed": allowed, "reasons": reasons, "limits": limits}
    return result
