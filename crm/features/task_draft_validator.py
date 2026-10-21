"""Follow-up task draft validator core (pure, deterministic)."""
_TITLE_REQUIRED = "title is required"
_TITLE_TYPE = "title must be a string"
_TITLE_TOO_LONG = "title must be at most 180 characters"
_DUE_REQUIRED = "due_date is required"
_DUE_INVALID = "due_date must be YYYY-MM-DD valid calendar date"
_COMPLETED_INVALID = "completed must be a boolean"
_DEAL_INVALID = "deal_pk must be an integer 1 to 9007199254740991 or null"
_MAX_TITLE_LEN = 180
_MIN_DEAL_PK = 1
_MAX_DEAL_PK = 9007199254740991
_STRIP_CHARS = " \t\n\r"
_PAYLOAD_ERROR = "payload must be an object"

def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError(_PAYLOAD_ERROR)
    errors = {}
    title_out = None
    due_out = None
    completed_out = False
    deal_out = None
    title_ok = False
    due_ok = False
    completed_ok = False
    deal_ok = False
    if "title" not in payload or payload["title"] is None:
        errors["title"] = _TITLE_REQUIRED
    else:
        raw_title = payload["title"]
        if not isinstance(raw_title, str):
            errors["title"] = _TITLE_TYPE
        else:
            trimmed = raw_title.strip(_STRIP_CHARS)
            if trimmed == "":
                errors["title"] = _TITLE_REQUIRED
            elif len(trimmed) > _MAX_TITLE_LEN:
                errors["title"] = _TITLE_TOO_LONG
            else:
                title_out = trimmed
                title_ok = True
    if "due_date" not in payload or payload["due_date"] is None or payload["due_date"] == "":
        errors["due_date"] = _DUE_REQUIRED
    else:
        raw_due = payload["due_date"]
        if not isinstance(raw_due, str):
            errors["due_date"] = _DUE_INVALID
        elif len(raw_due) != 10:
            errors["due_date"] = _DUE_INVALID
        elif raw_due[4] != "-" or raw_due[7] != "-":
            errors["due_date"] = _DUE_INVALID
        elif not ("0" <= raw_due[0] <= "9" and "0" <= raw_due[1] <= "9" and "0" <= raw_due[2] <= "9" and "0" <= raw_due[3] <= "9" and "0" <= raw_due[5] <= "9" and "0" <= raw_due[6] <= "9" and "0" <= raw_due[8] <= "9" and "0" <= raw_due[9] <= "9"):
            errors["due_date"] = _DUE_INVALID
        else:
            year = int(raw_due[0:4])
            month = int(raw_due[5:7])
            day = int(raw_due[8:10])
            if month < 1 or month > 12:
                errors["due_date"] = _DUE_INVALID
            else:
                if month == 2:
                    is_leap = (year % 400 == 0) or (year % 4 == 0 and year % 100 != 0)
                    if is_leap:
                        max_day = 29
                    else:
                        max_day = 28
                elif month == 4 or month == 6 or month == 9 or month == 11:
                    max_day = 30
                else:
                    max_day = 31
                if day < 1 or day > max_day:
                    errors["due_date"] = _DUE_INVALID
                else:
                    due_out = raw_due
                    due_ok = True
    if "completed" not in payload:
        completed_out = False
        completed_ok = True
    else:
        raw_completed = payload["completed"]
        if raw_completed is True or raw_completed is False:
            completed_out = raw_completed
            completed_ok = True
        else:
            errors["completed"] = _COMPLETED_INVALID
    if "deal_pk" not in payload or payload["deal_pk"] is None:
        deal_out = None
        deal_ok = True
    else:
        raw_deal = payload["deal_pk"]
        if raw_deal is True or raw_deal is False:
            errors["deal_pk"] = _DEAL_INVALID
        elif not isinstance(raw_deal, int):
            errors["deal_pk"] = _DEAL_INVALID
        elif raw_deal < _MIN_DEAL_PK or raw_deal > _MAX_DEAL_PK:
            errors["deal_pk"] = _DEAL_INVALID
        else:
            deal_out = raw_deal
            deal_ok = True
    if errors:
        return {"valid": False, "errors": errors, "normalized": None}
    if title_ok and due_ok and completed_ok and deal_ok:
        normalized = {"title": title_out, "due_date": due_out, "completed": completed_out, "deal_pk": deal_out}
        return {"valid": True, "errors": {}, "normalized": normalized}
    return {"valid": False, "errors": errors, "normalized": None}
