"""Record ownership isolation check core.

Pure deterministic snapshot helper. It mirrors OwnedRecord.validate_related_owners
for companies, contacts, deals and tasks so callers can check from pure JSON
that records and their links belong to one account.

The caller keeps database scoping, authentication, and all writes.
This function does no ownership enforcement, database query, CSV handling,
clock read, file access, or network access, and it never mutates inputs.
"""

OWNER_MIN = 1
OWNER_MAX = 9007199254740991
RECORD_LIMIT = 5000
ALLOWED_KINDS = ("company", "contact", "deal", "task")


def _is_safe_id(value):
    """Return True when value is a safe account or record identifier."""
    if type(value) is not int:
        return False
    if value < OWNER_MIN:
        return False
    if value > OWNER_MAX:
        return False
    return True


def _is_valid_link(value):
    """Return True when value is None or a safe identifier."""
    if value is None:
        return True
    if type(value) is not int:
        return False
    if value < OWNER_MIN:
        return False
    if value > OWNER_MAX:
        return False
    return True


def run_feature(payload):
    """Snapshot record ownership and link isolation for one owner.

    Expects an object with required owner safe int and optional records list.
    Returns owner, total_count, owned_count, isolated_count,
    accessible_count, and normalized results in input order.
    Raises ValueError on any malformed input or allowance violation.
    """
    if type(payload) is not dict:
        raise ValueError("payload must be an object")
    if "owner" not in payload:
        raise ValueError("owner is required")
    owner = payload["owner"]
    if _is_safe_id(owner) is False:
        raise ValueError("owner must be int in range 1 to 9007199254740991")
    if "records" in payload:
        records = payload["records"]
    else:
        records = []
    if type(records) is not list:
        raise ValueError("records must be a list")
    if len(records) > RECORD_LIMIT:
        raise ValueError("records exceeds 5000 item limit")
    results = []
    owned_count = 0
    isolated_count = 0
    accessible_count = 0
    for record in records:
        if type(record) is not dict:
            raise ValueError("record must be an object")
        if "kind" not in record:
            raise ValueError("record kind is required")
        if "pk" not in record:
            raise ValueError("record pk is required")
        if "owner" not in record:
            raise ValueError("record owner is required")
        kind = record["kind"]
        pk = record["pk"]
        rec_owner = record["owner"]
        if type(kind) is not str:
            raise ValueError("kind must be a string")
        if kind not in ALLOWED_KINDS:
            raise ValueError("unknown kind")
        if _is_safe_id(pk) is False:
            raise ValueError("pk must be int in range 1 to 9007199254740991")
        if _is_safe_id(rec_owner) is False:
            raise ValueError("record owner must be int in range 1 to 9007199254740991")
        if "company_owner" in record:
            company_owner = record["company_owner"]
        else:
            company_owner = None
        if "contact_owner" in record:
            contact_owner = record["contact_owner"]
        else:
            contact_owner = None
        if "deal_owner" in record:
            deal_owner = record["deal_owner"]
        else:
            deal_owner = None
        if _is_valid_link(company_owner) is False:
            raise ValueError("company_owner malformed")
        if _is_valid_link(contact_owner) is False:
            raise ValueError("contact_owner malformed")
        if _is_valid_link(deal_owner) is False:
            raise ValueError("deal_owner malformed")
        if kind == "company":
            if company_owner is not None:
                raise ValueError("company disallows company_owner")
            if contact_owner is not None:
                raise ValueError("company disallows contact_owner")
            if deal_owner is not None:
                raise ValueError("company disallows deal_owner")
            isolated = True
        elif kind == "contact":
            if contact_owner is not None:
                raise ValueError("contact disallows contact_owner")
            if deal_owner is not None:
                raise ValueError("contact disallows deal_owner")
            if company_owner is None:
                isolated = True
            elif company_owner == rec_owner:
                isolated = True
            else:
                isolated = False
        elif kind == "deal":
            if deal_owner is not None:
                raise ValueError("deal disallows deal_owner")
            if company_owner is None:
                company_ok = True
            elif company_owner == rec_owner:
                company_ok = True
            else:
                company_ok = False
            if contact_owner is None:
                contact_ok = True
            elif contact_owner == rec_owner:
                contact_ok = True
            else:
                contact_ok = False
            if company_ok and contact_ok:
                isolated = True
            else:
                isolated = False
        else:
            if company_owner is not None:
                raise ValueError("task disallows company_owner")
            if contact_owner is not None:
                raise ValueError("task disallows contact_owner")
            if deal_owner is None:
                isolated = True
            elif deal_owner == rec_owner:
                isolated = True
            else:
                isolated = False
        if rec_owner == owner:
            owned = True
        else:
            owned = False
        if owned and isolated:
            accessible = True
        else:
            accessible = False
        if owned:
            owned_count = owned_count + 1
        if isolated:
            isolated_count = isolated_count + 1
        if accessible:
            accessible_count = accessible_count + 1
        entry = {"kind": kind, "pk": pk, "owner": rec_owner, "company_owner": company_owner, "contact_owner": contact_owner, "deal_owner": deal_owner, "owned": owned, "isolated": isolated, "accessible": accessible}
        results = results + [entry]
    total_count = len(records)
    return {"owner": owner, "total_count": total_count, "owned_count": owned_count, "isolated_count": isolated_count, "accessible_count": accessible_count, "results": results}
