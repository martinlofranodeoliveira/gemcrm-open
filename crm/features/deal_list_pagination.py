"""Deal list pagination core: pure deterministic list helper."""

_PER_PAGE = 50
_MAX_DEALS = 5000
_MAX_TITLE_LEN = 180
_MAX_Q_INPUT = 5000
_MAX_Q = 200
_MAX_PK = 9007199254740991
_STRIP_CHARS = " \t\n\r"
_STAGES = ("new", "qualified", "proposal", "won", "lost")
_ALL_STAGE = "all"


def _is_all_digits(s):
    if s == "":
        return False
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c < "0" or c > "9":
            return False
        i = i + 1
    return True


def _is_page_int_string(s):
    if s == "":
        return False
    if s[0] == "-":
        rest = s[1:]
        return _is_all_digits(rest)
    return _is_all_digits(s)


def _sort_key(item):
    return (item["title"].casefold(), item["title"], item["pk"])


def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError("payload must be object")
    if "deals" in payload:
        deals_raw = payload["deals"]
    else:
        deals_raw = []
    if not isinstance(deals_raw, list):
        raise ValueError("deals must be list")
    if len(deals_raw) > _MAX_DEALS:
        raise ValueError("deals too large")
    seen = {}
    cleaned = []
    for entry in deals_raw:
        if not isinstance(entry, dict):
            raise ValueError("deal must be object")
        if "pk" not in entry:
            raise ValueError("pk missing")
        if "title" not in entry:
            raise ValueError("title missing")
        if "stage" not in entry:
            raise ValueError("stage missing")
        pk = entry["pk"]
        title = entry["title"]
        stage = entry["stage"]
        if type(pk) is not int:
            raise ValueError("pk must be int")
        if pk < 1 or pk > _MAX_PK:
            raise ValueError("pk out of range")
        if pk in seen:
            raise ValueError("duplicate pk")
        seen[pk] = True
        if not isinstance(title, str):
            raise ValueError("title must be str")
        if len(title) > _MAX_TITLE_LEN:
            raise ValueError("title too long")
        if not isinstance(stage, str):
            raise ValueError("deal stage must be str")
        if stage not in _STAGES:
            raise ValueError("bad deal stage")
        cleaned.append({"pk": pk, "title": title, "stage": stage})
    if "q" not in payload:
        q_norm = ""
    else:
        q_raw = payload["q"]
        if q_raw is None:
            q_norm = ""
        else:
            if not isinstance(q_raw, str):
                raise ValueError("q must be str or None")
            if len(q_raw) > _MAX_Q_INPUT:
                raise ValueError("q too long")
            q_norm = q_raw.strip(_STRIP_CHARS)
            q_norm = q_norm[:_MAX_Q]
    if "stage" not in payload:
        stage_norm = _ALL_STAGE
    else:
        stage_raw = payload["stage"]
        if stage_raw is None:
            stage_norm = _ALL_STAGE
        else:
            if not isinstance(stage_raw, str):
                raise ValueError("stage must be str or None")
            s = stage_raw.strip(_STRIP_CHARS)
            if s == "" or s == _ALL_STAGE:
                stage_norm = _ALL_STAGE
            else:
                if s not in _STAGES:
                    raise ValueError("bad stage filter")
                stage_norm = s
    if "page" not in payload:
        page_value = 1
        page_is_integer = True
    else:
        page_raw = payload["page"]
        if page_raw is None:
            page_value = 1
            page_is_integer = True
        else:
            if type(page_raw) is int:
                page_value = page_raw
                page_is_integer = True
            else:
                if isinstance(page_raw, str):
                    t = page_raw.strip(_STRIP_CHARS)
                    if t == "":
                        page_value = 1
                        page_is_integer = True
                    else:
                        if _is_page_int_string(t):
                            page_value = int(t)
                            page_is_integer = True
                        else:
                            page_value = 1
                            page_is_integer = False
                else:
                    raise ValueError("page must be int str or None")
    if q_norm == "":
        qfold = ""
    else:
        qfold = q_norm.casefold()
    filtered = []
    for item in cleaned:
        if stage_norm != _ALL_STAGE:
            if item["stage"] != stage_norm:
                continue
        if q_norm != "":
            if qfold not in item["title"].casefold():
                continue
        filtered.append(item)
    filtered.sort(key=_sort_key)
    total_count = len(filtered)
    num_pages = (total_count + _PER_PAGE - 1) // _PER_PAGE
    if num_pages < 1:
        num_pages = 1
    if page_is_integer:
        if page_value < 1 or page_value > num_pages:
            effective = num_pages
        else:
            effective = page_value
    else:
        effective = 1
    start = (effective - 1) * _PER_PAGE
    end = start + _PER_PAGE
    window = filtered[start:end]
    results = []
    for it in window:
        results.append({"pk": it["pk"], "title": it["title"], "stage": it["stage"]})
    if effective > 1:
        has_previous = True
        prev_page = effective - 1
    else:
        has_previous = False
        prev_page = None
    if effective < num_pages:
        has_next = True
        next_page = effective + 1
    else:
        has_next = False
        next_page = None
    return {"q": q_norm, "stage": stage_norm, "page": effective, "per_page": _PER_PAGE, "num_pages": num_pages, "total_count": total_count, "results": results, "has_previous": has_previous, "has_next": has_next, "prev_page": prev_page, "next_page": next_page}
