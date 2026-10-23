# Contact draft validator core: pure deterministic hint, no IO.
_MAX_RAW = 10000
_MAX_NAME = 180
_MAX_EMAIL = 254
_MAX_PHONE = 40
_MAX_COMPANY = 180
_MAX_NOTES = 2000
_STRIP_CHARS = " \t\n\r"
_PHONE_CHARS = "0123456789 +-.()/"
_DIGITS = "0123456789"

def _coerce_raw(value):
    # Missing or None defaults to empty string, str checked for bounds.
    if value is None:
        return ""
    if isinstance(value, str):
        if len(value) > _MAX_RAW:
            raise ValueError("raw field too long")
        return value
    raise ValueError("field must be str or None")

def _trim_text(value):
    return value.strip(_STRIP_CHARS)

def _email_problem(value):
    if len(value) == 0:
        return ""
    if len(value) > _MAX_EMAIL:
        return "too_long"
    if value.count("@") != 1:
        return "invalid"
    parts = value.split("@")
    local = parts[0]
    domain = parts[1]
    if len(local) == 0:
        return "invalid"
    if len(domain) == 0:
        return "invalid"
    if " " in value:
        return "invalid"
    if "\t" in value:
        return "invalid"
    if "\n" in value:
        return "invalid"
    if "\r" in value:
        return "invalid"
    if "." not in domain:
        return "invalid"
    if domain.startswith("."):
        return "invalid"
    if domain.endswith("."):
        return "invalid"
    if ".." in domain:
        return "invalid"
    suffix_parts = domain.split(".")
    suffix = suffix_parts[len(suffix_parts) - 1]
    if len(suffix) < 2:
        return "invalid"
    return ""

def _phone_problem(value):
    if len(value) == 0:
        return ""
    if len(value) > _MAX_PHONE:
        return "too_long"
    found_digit = False
    for ch in value:
        if ch in _DIGITS:
            found_digit = True
        if ch not in _PHONE_CHARS:
            return "invalid"
    if found_digit is False:
        return "invalid"
    return ""

def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    raw_name = _coerce_raw(payload.get("name", ""))
    raw_email = _coerce_raw(payload.get("email", ""))
    raw_phone = _coerce_raw(payload.get("phone", ""))
    raw_company = _coerce_raw(payload.get("company", ""))
    raw_notes = _coerce_raw(payload.get("notes", ""))
    norm_name = _trim_text(raw_name)
    norm_email = _trim_text(raw_email)
    norm_phone = _trim_text(raw_phone)
    norm_company = _trim_text(raw_company)
    norm_notes = _trim_text(raw_notes)
    errors = {}
    if len(norm_name) == 0:
        errors["name"] = "required"
    else:
        if len(norm_name) > _MAX_NAME:
            errors["name"] = "too_long"
    email_issue = _email_problem(norm_email)
    if len(email_issue) != 0:
        errors["email"] = email_issue
    phone_issue = _phone_problem(norm_phone)
    if len(phone_issue) != 0:
        errors["phone"] = phone_issue
    if len(norm_company) != 0:
        if len(norm_company) > _MAX_COMPANY:
            errors["company"] = "too_long"
    if len(norm_notes) > _MAX_NOTES:
        errors["notes"] = "too_long"
    normalized = {}
    normalized["name"] = norm_name
    normalized["email"] = norm_email
    normalized["phone"] = norm_phone
    normalized["company"] = norm_company
    normalized["notes"] = norm_notes
    valid = len(errors) == 0
    result = {}
    result["valid"] = valid
    result["errors"] = errors
    result["normalized"] = normalized
    return result
