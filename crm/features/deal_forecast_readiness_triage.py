"""Deal forecast readiness triage core."""
VALID_STAGES = ("new", "qualified", "proposal", "won", "lost")
OPEN_STAGES = ("new", "qualified", "proposal")
DIGITS = "0123456789"
MAX_PK = 9007199254740991
MIN_PK = 1
MAX_DEALS = 100


def _is_leap_year(year):
    if year % 400 == 0:
        return True
    if year % 100 == 0:
        return False
    if year % 4 == 0:
        return True
    return False


def _days_in_month(year, month):
    if month == 1:
        return 31
    if month == 2:
        if _is_leap_year(year):
            return 29
        return 28
    if month == 3:
        return 31
    if month == 4:
        return 30
    if month == 5:
        return 31
    if month == 6:
        return 30
    if month == 7:
        return 31
    if month == 8:
        return 31
    if month == 9:
        return 30
    if month == 10:
        return 31
    if month == 11:
        return 30
    if month == 12:
        return 31
    return 0


def _is_valid_date_string(value):
    if not isinstance(value, str):
        return False
    if len(value) != 10:
        return False
    if value[4] != "-":
        return False
    if value[7] != "-":
        return False
    if value[0] not in DIGITS:
        return False
    if value[1] not in DIGITS:
        return False
    if value[2] not in DIGITS:
        return False
    if value[3] not in DIGITS:
        return False
    if value[5] not in DIGITS:
        return False
    if value[6] not in DIGITS:
        return False
    if value[8] not in DIGITS:
        return False
    if value[9] not in DIGITS:
        return False
    year = int(value[0:4])
    month = int(value[5:7])
    day = int(value[8:10])
    if month < 1:
        return False
    if month > 12:
        return False
    limit = _days_in_month(year, month)
    if day < 1:
        return False
    if day > limit:
        return False
    return True


def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError("payload must be object")
    if "today" not in payload:
        raise ValueError("today is required")
    today = payload["today"]
    if not _is_valid_date_string(today):
        raise ValueError("today must be YYYY-MM-DD")
    if "deals" not in payload:
        deals = []
    else:
        deals = payload["deals"]
    if deals is None:
        raise ValueError("deals must be list")
    if not isinstance(deals, list):
        raise ValueError("deals must be list")
    if len(deals) > MAX_DEALS:
        raise ValueError("too many deals")
    seen_pks = []
    missing_pks = []
    overdue_pks = []
    due_today_pks = []
    upcoming_pks = []
    open_count = 0
    closed_count = 0
    for deal in deals:
        if not isinstance(deal, dict):
            raise ValueError("deal must be object")
        if "pk" not in deal:
            raise ValueError("pk is required")
        if "stage" not in deal:
            raise ValueError("stage is required")
        if "expected_close" not in deal:
            raise ValueError("expected_close is required")
        pk = deal["pk"]
        stage = deal["stage"]
        expected_close = deal["expected_close"]
        if type(pk) is not int:
            raise ValueError("pk must be int")
        if pk < MIN_PK:
            raise ValueError("pk out of range")
        if pk > MAX_PK:
            raise ValueError("pk out of range")
        if not isinstance(stage, str):
            raise ValueError("stage must be str")
        if stage not in VALID_STAGES:
            raise ValueError("stage unknown")
        if expected_close is None:
            pass
        else:
            if not isinstance(expected_close, str):
                raise ValueError("expected_close must be str or null")
            if not _is_valid_date_string(expected_close):
                raise ValueError("expected_close must be YYYY-MM-DD or null")
        if pk in seen_pks:
            raise ValueError("duplicate pk")
        seen_pks.append(pk)
        if stage in OPEN_STAGES:
            open_count = open_count + 1
            if expected_close is None:
                missing_pks.append(pk)
            else:
                if expected_close < today:
                    overdue_pks.append(pk)
                else:
                    if expected_close == today:
                        due_today_pks.append(pk)
                    else:
                        upcoming_pks.append(pk)
        else:
            closed_count = closed_count + 1
    deal_count = len(deals)
    missing_sorted = sorted(missing_pks)
    overdue_sorted = sorted(overdue_pks)
    due_today_sorted = sorted(due_today_pks)
    upcoming_sorted = sorted(upcoming_pks)
    result = {}
    result["deal_count"] = deal_count
    result["open_count"] = open_count
    result["closed_count"] = closed_count
    result["missing_count"] = len(missing_sorted)
    result["overdue_count"] = len(overdue_sorted)
    result["due_today_count"] = len(due_today_sorted)
    result["upcoming_count"] = len(upcoming_sorted)
    result["missing_pks"] = missing_sorted
    result["overdue_pks"] = overdue_sorted
    result["due_today_pks"] = due_today_sorted
    result["upcoming_pks"] = upcoming_sorted
    return result
