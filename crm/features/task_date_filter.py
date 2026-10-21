_MAX_TASKS = 5000
_MAX_PK = 9007199254740991
_MAX_TITLE_LEN = 180
_MAX_Q_LEN = 200
_ALLOWED_STATUSES = ("all", "open", "overdue", "today", "upcoming", "completed")


def _is_leap_year(year):
    if year % 4 != 0:
        return False
    if year % 100 != 0:
        return True
    if year % 400 != 0:
        return False
    return True


def _days_in_month(year, month):
    if month == 2:
        if _is_leap_year(year):
            return 29
        return 28
    if month == 4:
        return 30
    if month == 6:
        return 30
    if month == 9:
        return 30
    if month == 11:
        return 30
    return 31


def _is_valid_date_string(value):
    if not isinstance(value, str):
        return False
    if len(value) != 10:
        return False
    if value[4] != "-":
        return False
    if value[7] != "-":
        return False
    for pos in (0, 1, 2, 3, 5, 6, 8, 9):
        ch = value[pos]
        if ch < "0":
            return False
        if ch > "9":
            return False
    year = int(value[0:4])
    month = int(value[5:7])
    day = int(value[8:10])
    if month < 1:
        return False
    if month > 12:
        return False
    dim = _days_in_month(year, month)
    if day < 1:
        return False
    if day > dim:
        return False
    return True


def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError("payload must be object")
    if "tasks" in payload:
        tasks = payload["tasks"]
    else:
        tasks = []
    if "today" in payload:
        today = payload["today"]
    else:
        raise ValueError("today is required")
    if "status" in payload:
        status = payload["status"]
    else:
        status = None
    if "q" in payload:
        q_raw = payload["q"]
    else:
        q_raw = None
    if not isinstance(tasks, list):
        raise ValueError("tasks must be list")
    if len(tasks) > _MAX_TASKS:
        raise ValueError("too many tasks")
    if status is not None:
        if not isinstance(status, str):
            raise ValueError("status must be str or None")
    if q_raw is not None:
        if not isinstance(q_raw, str):
            raise ValueError("q must be str or None")
    if not isinstance(today, str):
        raise ValueError("today must be str")
    if not _is_valid_date_string(today):
        raise ValueError("today must be valid date")
    if status is None:
        status_effective = "all"
    else:
        if status in _ALLOWED_STATUSES:
            status_effective = status
        else:
            status_effective = "all"
    if q_raw is None:
        q = ""
    else:
        q_stripped = q_raw.strip()
        q = q_stripped[:_MAX_Q_LEN]
    for item in tasks:
        if not isinstance(item, dict):
            raise ValueError("task must be object")
        if "pk" not in item:
            raise ValueError("task pk missing")
        if "title" not in item:
            raise ValueError("task title missing")
        if "due_date" not in item:
            raise ValueError("task due_date missing")
        if "completed" not in item:
            raise ValueError("task completed missing")
        pk = item["pk"]
        title = item["title"]
        due_date = item["due_date"]
        completed = item["completed"]
        if isinstance(pk, bool):
            raise ValueError("task pk invalid")
        if not isinstance(pk, int):
            raise ValueError("task pk invalid")
        if pk < 1:
            raise ValueError("task pk invalid")
        if pk > _MAX_PK:
            raise ValueError("task pk invalid")
        if not isinstance(title, str):
            raise ValueError("task title invalid")
        if len(title) < 1:
            raise ValueError("task title invalid")
        if len(title) > _MAX_TITLE_LEN:
            raise ValueError("task title invalid")
        if not isinstance(due_date, str):
            raise ValueError("task due_date invalid")
        if not _is_valid_date_string(due_date):
            raise ValueError("task due_date invalid")
        if completed is not True:
            if completed is not False:
                raise ValueError("task completed invalid")
    kept = []
    for item in tasks:
        completed = item["completed"]
        due_date = item["due_date"]
        keep = True
        if status_effective == "all":
            keep = True
        elif status_effective == "open":
            if completed is not False:
                keep = False
        elif status_effective == "completed":
            if completed is not True:
                keep = False
        elif status_effective == "overdue":
            if completed is not False:
                keep = False
            elif not due_date < today:
                keep = False
        elif status_effective == "today":
            if completed is not False:
                keep = False
            elif not due_date == today:
                keep = False
        elif status_effective == "upcoming":
            if completed is not False:
                keep = False
            elif not due_date > today:
                keep = False
        if keep is False:
            continue
        if q != "":
            title = item["title"]
            needle = q.casefold()
            hay = title.casefold()
            if needle not in hay:
                keep = False
        if keep:
            kept.append(item)
    order_keys = []
    for pos in range(len(kept)):
        item = kept[pos]
        completed = item["completed"]
        flag = 1
        if completed is False:
            flag = 0
        order_keys.append((flag, item["due_date"], item["pk"], pos))
    order_keys.sort()
    sorted_kept = []
    for tup in order_keys:
        pos = tup[3]
        sorted_kept.append(kept[pos])
    results = []
    for item in sorted_kept:
        entry = {}
        entry["pk"] = item["pk"]
        entry["title"] = item["title"]
        entry["due_date"] = item["due_date"]
        entry["completed"] = item["completed"]
        results.append(entry)
    output = {}
    output["today"] = today
    output["status_effective"] = status_effective
    output["q"] = q
    output["total_count"] = len(tasks)
    output["filtered_count"] = len(results)
    output["results"] = results
    return output
