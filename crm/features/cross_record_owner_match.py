"""Cross-record owner match core."""
_ALLOWED_FIELDS = ("company", "contact", "deal")
_MESSAGE = "Escolha um registro da sua conta."


def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError("payload must be dict")
    if "owner_id" not in payload:
        raise ValueError("owner_id is required")
    owner_id = payload["owner_id"]
    if type(owner_id) is not int:
        raise ValueError("owner_id must be int")
    if owner_id < 1:
        raise ValueError("owner_id must be >= 1")
    if "links" not in payload:
        links = []
    else:
        links = payload["links"]
    if links is None:
        raise ValueError("links must be list")
    if not isinstance(links, list):
        raise ValueError("links must be list")
    if len(links) > 10:
        raise ValueError("links too long")
    seen = []
    errors = {}
    for link in links:
        if not isinstance(link, dict):
            raise ValueError("link must be dict")
        if "field" not in link:
            raise ValueError("field is required")
        field = link["field"]
        if not isinstance(field, str):
            raise ValueError("field must be str")
        if field not in _ALLOWED_FIELDS:
            raise ValueError("unknown field")
        if field in seen:
            raise ValueError("duplicate field")
        seen = seen + [field]
        if "related_owner_id" not in link:
            related_owner_id = None
        else:
            related_owner_id = link["related_owner_id"]
        if related_owner_id is None:
            continue
        if type(related_owner_id) is not int:
            raise ValueError("related_owner_id must be int")
        if related_owner_id < 1:
            raise ValueError("related_owner_id must be >= 1")
        if related_owner_id != owner_id:
            errors[field] = _MESSAGE
    checked = len(links)
    violated = len(errors)
    valid = len(errors) == 0
    return {"owner_id": owner_id, "checked": checked, "violated": violated, "valid": valid, "errors": errors}
