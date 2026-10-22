_PER_PAGE = 50
_MAX_COMPANIES = 5000
_MAX_Q_RAW = 5000
_MAX_Q_NORM = 200
_MAX_NAME_LEN = 180
_MIN_PK = 1
_MAX_PK = 9007199254740991
_STRIP_CHARS = " \t\n\r"
_DIGITS = "0123456789"


def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError("payload must be object")
    if "companies" in payload:
        companies_raw = payload["companies"]
    else:
        companies_raw = []
    if "q" in payload:
        q_raw = payload["q"]
    else:
        q_raw = None
    if "page" in payload:
        page_raw = payload["page"]
    else:
        page_raw = None
    if not isinstance(companies_raw, list):
        raise ValueError("companies must be list")
    if len(companies_raw) > _MAX_COMPANIES:
        raise ValueError("companies too large")
    if q_raw is None:
        q_norm = ""
    else:
        if not isinstance(q_raw, str):
            raise ValueError("q must be str")
        if len(q_raw) > _MAX_Q_RAW:
            raise ValueError("q too large")
        q_norm = q_raw.strip(_STRIP_CHARS)[:_MAX_Q_NORM]
    page_value = 1
    page_is_integer = True
    if page_raw is None:
        page_value = 1
        page_is_integer = True
    else:
        if isinstance(page_raw, bool):
            raise ValueError("page bad type")
        else:
            if isinstance(page_raw, int):
                page_value = page_raw
                page_is_integer = True
            else:
                if isinstance(page_raw, str):
                    s = page_raw.strip(_STRIP_CHARS)
                    if s == "":
                        page_value = 1
                        page_is_integer = True
                    else:
                        if s[0] == "-":
                            body = s[1:]
                            if body == "":
                                page_value = 1
                                page_is_integer = False
                            else:
                                ok = True
                                for ch in body:
                                    if ch not in _DIGITS:
                                        ok = False
                                        break
                                if ok:
                                    page_value = int(s)
                                    page_is_integer = True
                                else:
                                    page_value = 1
                                    page_is_integer = False
                        else:
                            ok = True
                            for ch in s:
                                if ch not in _DIGITS:
                                    ok = False
                                    break
                            if ok:
                                page_value = int(s)
                                page_is_integer = True
                            else:
                                page_value = 1
                                page_is_integer = False
                else:
                    raise ValueError("page bad type")
    seen = {}
    rows = []
    for entry in companies_raw:
        if not isinstance(entry, dict):
            raise ValueError("entry must be object")
        if "pk" not in entry:
            raise ValueError("pk missing")
        if "name" not in entry:
            raise ValueError("name missing")
        pk = entry["pk"]
        name = entry["name"]
        if isinstance(pk, bool):
            raise ValueError("pk bad type")
        if not isinstance(pk, int):
            raise ValueError("pk bad type")
        if pk < _MIN_PK:
            raise ValueError("pk out of range")
        if pk > _MAX_PK:
            raise ValueError("pk out of range")
        if not isinstance(name, str):
            raise ValueError("name bad type")
        if len(name) > _MAX_NAME_LEN:
            raise ValueError("name too large")
        if pk in seen:
            raise ValueError("duplicate pk")
        seen[pk] = True
        rows.append((name.casefold(), name, pk))
    if q_norm == "":
        filtered = []
        for r in rows:
            filtered.append(r)
    else:
        qfold = q_norm.casefold()
        filtered = []
        for r in rows:
            if qfold in r[0]:
                filtered.append(r)
    ordered = sorted(filtered)
    total = len(ordered)
    if total == 0:
        num_pages = 1
    else:
        num_pages = (total + _PER_PAGE - 1) // _PER_PAGE
        if num_pages < 1:
            num_pages = 1
    if page_is_integer:
        if page_value < 1:
            eff = num_pages
        else:
            if page_value > num_pages:
                eff = num_pages
            else:
                eff = page_value
    else:
        eff = 1
    start = (eff - 1) * _PER_PAGE
    end = start + _PER_PAGE
    sliced = ordered[start:end]
    results = []
    for t in sliced:
        results.append({"pk": t[2], "name": t[1]})
    if eff > 1:
        has_prev = True
        prev_p = eff - 1
    else:
        has_prev = False
        prev_p = None
    if eff < num_pages:
        has_next = True
        next_p = eff + 1
    else:
        has_next = False
        next_p = None
    return {"q": q_norm, "page": eff, "per_page": _PER_PAGE, "num_pages": num_pages, "total_count": total, "results": results, "has_previous": has_prev, "has_next": has_next, "prev_page": prev_p, "next_page": next_p}
