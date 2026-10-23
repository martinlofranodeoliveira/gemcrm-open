_STRIP_CHARS = " \t\n\r"
_MAX_TASKS = 500
_MAX_RAW_TITLE = 10000
_MAX_NORMALIZED = 180
_MIN_PK = 1
_MIN_DEAL = 1
_DATE_LEN = 10
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
    return 31
def _is_digit_char(ch):
    if ch >= "0" and ch <= "9":
        return True
    return False
def _validate_due_date(value):
    if type(value) is not str:
        raise ValueError("due_date must be str")
    if len(value) != _DATE_LEN:
        raise ValueError("due_date must be YYYY-MM-DD")
    if value[4] != "-":
        raise ValueError("due_date must be YYYY-MM-DD")
    if value[7] != "-":
        raise ValueError("due_date must be YYYY-MM-DD")
    if not _is_digit_char(value[0]):
        raise ValueError("due_date must be YYYY-MM-DD")
    if not _is_digit_char(value[1]):
        raise ValueError("due_date must be YYYY-MM-DD")
    if not _is_digit_char(value[2]):
        raise ValueError("due_date must be YYYY-MM-DD")
    if not _is_digit_char(value[3]):
        raise ValueError("due_date must be YYYY-MM-DD")
    if not _is_digit_char(value[5]):
        raise ValueError("due_date must be YYYY-MM-DD")
    if not _is_digit_char(value[6]):
        raise ValueError("due_date must be YYYY-MM-DD")
    if not _is_digit_char(value[8]):
        raise ValueError("due_date must be YYYY-MM-DD")
    if not _is_digit_char(value[9]):
        raise ValueError("due_date must be YYYY-MM-DD")
    year = int(value[0:4])
    month = int(value[5:7])
    day = int(value[8:10])
    if year < 1:
        raise ValueError("due_date year out of range")
    if year > 9999:
        raise ValueError("due_date year out of range")
    if month < 1:
        raise ValueError("due_date month out of range")
    if month > 12:
        raise ValueError("due_date month out of range")
    dim = _days_in_month(year, month)
    if day < 1:
        raise ValueError("due_date day out of range")
    if day > dim:
        raise ValueError("due_date day out of range")
    return value
def _normalize_title(raw):
    if type(raw) is not str:
        raise ValueError("title must be str")
    if len(raw) > _MAX_RAW_TITLE:
        raise ValueError("title too long")
    normalized = raw.strip(_STRIP_CHARS).casefold()
    if len(normalized) < 1:
        raise ValueError("title empty after normalize")
    if len(normalized) > _MAX_NORMALIZED:
        raise ValueError("title normalized too long")
    return normalized
def _sort_pks_ascending(values):
    result = []
    for v in values:
        result.append(v)
    for i in range(1, len(result)):
        cur = result[i]
        j = i - 1
        while j >= 0 and result[j] > cur:
            result[j + 1] = result[j]
            j = j - 1
        result[j + 1] = cur
    return result
def _group_less(a, b):
    if a["due_date"] != b["due_date"]:
        if a["due_date"] < b["due_date"]:
            return True
        return False
    if a["title_normalized"] != b["title_normalized"]:
        if a["title_normalized"] < b["title_normalized"]:
            return True
        return False
    da = a["deal"]
    db = b["deal"]
    if da is None and db is None:
        return False
    if da is None:
        return True
    if db is None:
        return False
    if da < db:
        return True
    return False
def run_feature(payload):
    if type(payload) is not dict:
        raise ValueError("payload must be object")
    if "tasks" in payload:
        tasks = payload["tasks"]
    else:
        tasks = []
    if type(tasks) is not list:
        raise ValueError("tasks must be list")
    if len(tasks) > _MAX_TASKS:
        raise ValueError("too many tasks")
    seen_pks = {}
    parsed_titles = []
    parsed_dues = []
    parsed_deals = []
    parsed_pks = []
    for task in tasks:
        if type(task) is not dict:
            raise ValueError("task must be object")
        if "pk" not in task:
            raise ValueError("pk missing")
        pk = task["pk"]
        if type(pk) is not int:
            raise ValueError("pk must be int")
        if pk < _MIN_PK:
            raise ValueError("pk must be >= 1")
        if pk in seen_pks:
            raise ValueError("duplicate pk")
        seen_pks[pk] = True
        if "title" not in task:
            raise ValueError("title missing")
        raw_title = task["title"]
        norm = _normalize_title(raw_title)
        if "due_date" not in task:
            raise ValueError("due_date missing")
        due = task["due_date"]
        _validate_due_date(due)
        if "deal" not in task:
            deal = None
        else:
            dv = task["deal"]
            if dv is None:
                deal = None
            else:
                if type(dv) is not int:
                    raise ValueError("deal must be int or null")
                if dv < _MIN_DEAL:
                    raise ValueError("deal must be >= 1")
                deal = dv
        if "completed" not in task:
            raise ValueError("completed missing")
        comp = task["completed"]
        if type(comp) is not bool:
            raise ValueError("completed must be bool")
        parsed_titles.append(norm)
        parsed_dues.append(due)
        parsed_deals.append(deal)
        parsed_pks.append(pk)
    groups_map = {}
    groups_order = []
    for i in range(len(parsed_pks)):
        t = parsed_titles[i]
        d = parsed_dues[i]
        dl = parsed_deals[i]
        p = parsed_pks[i]
        key = (t, d, dl)
        if key in groups_map:
            grp = groups_map[key]
            plist = grp["task_pks"]
            plist.append(p)
        else:
            grp = {"title_normalized": t, "due_date": d, "deal": dl, "task_pks": [p]}
            groups_map[key] = grp
            groups_order.append(key)
    kept = []
    for key in groups_order:
        grp = groups_map[key]
        pks = grp["task_pks"]
        sorted_pks = _sort_pks_ascending(pks)
        if len(sorted_pks) > 1:
            kept.append({"title_normalized": grp["title_normalized"], "due_date": grp["due_date"], "deal": grp["deal"], "count": len(sorted_pks), "task_pks": sorted_pks})
    for i in range(1, len(kept)):
        cur = kept[i]
        j = i - 1
        while j >= 0 and _group_less(cur, kept[j]):
            kept[j + 1] = kept[j]
            j = j - 1
        kept[j + 1] = cur
    total = len(tasks)
    gcount = len(kept)
    tcount = 0
    for g in kept:
        tcount = tcount + g["count"]
    return {"total_tasks": total, "duplicate_group_count": gcount, "duplicate_task_count": tcount, "groups": kept}
