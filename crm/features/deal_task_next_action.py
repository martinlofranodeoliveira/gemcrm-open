MAX_DEALS = 2000
MAX_TASKS = 5000
MAX_RAW_TITLE_LEN = 10000
MAX_TRIMMED_TITLE_LEN = 180
MIN_PK = 1


def _is_leap_year(year):
    if year % 400 == 0:
        return True
    if year % 100 == 0:
        return False
    if year % 4 == 0:
        return True
    return False


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


def _validate_due_date(value):
    if not isinstance(value, str):
        raise ValueError("due_date must be str")
    if len(value) != 10:
        raise ValueError("due_date must be YYYY-MM-DD")
    if value[4] != "-":
        raise ValueError("due_date must be YYYY-MM-DD")
    if value[7] != "-":
        raise ValueError("due_date must be YYYY-MM-DD")
    for idx in (0, 1, 2, 3, 5, 6, 8, 9):
        ch = value[idx]
        if ch < "0":
            raise ValueError("due_date digits")
        if ch > "9":
            raise ValueError("due_date digits")
    year = int(value[0:4])
    month = int(value[5:7])
    day = int(value[8:10])
    if year < 1:
        raise ValueError("due_date year")
    if year > 9999:
        raise ValueError("due_date year")
    if month < 1:
        raise ValueError("due_date month")
    if month > 12:
        raise ValueError("due_date month")
    dim = _days_in_month(year, month)
    if day < 1:
        raise ValueError("due_date day")
    if day > dim:
        raise ValueError("due_date day")


def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError("payload must be object")
    if "deals" in payload:
        deals = payload["deals"]
    else:
        deals = []
    if "tasks" in payload:
        tasks = payload["tasks"]
    else:
        tasks = []
    if not isinstance(deals, list):
        raise ValueError("deals must be list")
    if not isinstance(tasks, list):
        raise ValueError("tasks must be list")
    if len(deals) > MAX_DEALS:
        raise ValueError("too many deals")
    if len(tasks) > MAX_TASKS:
        raise ValueError("too many tasks")
    deal_pks = []
    deal_titles = []
    seen_deals = set()
    for item in deals:
        if not isinstance(item, dict):
            raise ValueError("deal must be object")
        if "pk" not in item:
            raise ValueError("deal pk missing")
        if "title" not in item:
            raise ValueError("deal title missing")
        pk = item["pk"]
        raw = item["title"]
        if type(pk) is not int:
            raise ValueError("deal pk must be int")
        if pk < MIN_PK:
            raise ValueError("deal pk bounds")
        if not isinstance(raw, str):
            raise ValueError("deal title must be str")
        if len(raw) > MAX_RAW_TITLE_LEN:
            raise ValueError("deal title too long")
        trimmed = raw.strip(" \t\n\r")
        if len(trimmed) < 1:
            raise ValueError("deal title empty")
        if len(trimmed) > MAX_TRIMMED_TITLE_LEN:
            raise ValueError("deal title too long")
        if pk in seen_deals:
            raise ValueError("duplicate deal pk")
        seen_deals.add(pk)
        deal_pks.append(pk)
        deal_titles.append(trimmed)
    task_pks = []
    task_titles = []
    task_dues = []
    task_comps = []
    task_links = []
    seen_tasks = set()
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
        raw = item["title"]
        due = item["due_date"]
        comp = item["completed"]
        if "deal" in item:
            link = item["deal"]
        else:
            link = None
        if type(pk) is not int:
            raise ValueError("task pk must be int")
        if pk < MIN_PK:
            raise ValueError("task pk bounds")
        if not isinstance(raw, str):
            raise ValueError("task title must be str")
        if len(raw) > MAX_RAW_TITLE_LEN:
            raise ValueError("task title too long")
        trimmed = raw.strip(" \t\n\r")
        if len(trimmed) < 1:
            raise ValueError("task title empty")
        if len(trimmed) > MAX_TRIMMED_TITLE_LEN:
            raise ValueError("task title too long")
        if pk in seen_tasks:
            raise ValueError("duplicate task pk")
        seen_tasks.add(pk)
        if not isinstance(due, str):
            raise ValueError("due_date must be str")
        _validate_due_date(due)
        if type(comp) is not bool:
            raise ValueError("completed must be bool")
        if link is None:
            norm_link = None
        else:
            if type(link) is not int:
                raise ValueError("deal link must be int or null")
            if link < MIN_PK:
                raise ValueError("deal link bounds")
            norm_link = link
        task_pks.append(pk)
        task_titles.append(trimmed)
        task_dues.append(due)
        task_comps.append(comp)
        task_links.append(norm_link)
    total_open = 0
    for idx in range(len(task_pks)):
        if task_comps[idx] is False:
            total_open = total_open + 1
    results = []
    with_open = 0
    for d_idx in range(len(deal_pks)):
        dpk = deal_pks[d_idx]
        dtitle = deal_titles[d_idx]
        count = 0
        best_pk = None
        best_title = None
        best_due = None
        for t_idx in range(len(task_pks)):
            if task_comps[t_idx] is False:
                tlink = task_links[t_idx]
                if tlink is not None:
                    if tlink == dpk:
                        count = count + 1
                        tdue = task_dues[t_idx]
                        tpk = task_pks[t_idx]
                        ttitle = task_titles[t_idx]
                        if best_pk is None:
                            best_pk = tpk
                            best_title = ttitle
                            best_due = tdue
                        else:
                            if tdue < best_due:
                                best_pk = tpk
                                best_title = ttitle
                                best_due = tdue
                            else:
                                if tdue == best_due:
                                    if tpk < best_pk:
                                        best_pk = tpk
                                        best_title = ttitle
                                        best_due = tdue
        has_open = count > 0
        if has_open:
            with_open = with_open + 1
        entry = {}
        entry["deal_pk"] = dpk
        entry["deal_title"] = dtitle
        entry["has_open"] = has_open
        entry["open_count"] = count
        entry["next_pk"] = best_pk
        entry["next_title"] = best_title
        entry["next_due_date"] = best_due
        results.append(entry)
    total_deals = len(deal_pks)
    without_open = total_deals - with_open
    out = {}
    out["total_deals"] = total_deals
    out["deals_with_open"] = with_open
    out["deals_without_open"] = without_open
    out["total_open_tasks"] = total_open
    out["results"] = results
    return out
