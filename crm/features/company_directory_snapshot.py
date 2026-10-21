"""Company directory snapshot core."""

_MAX_PK = 9007199254740991
_MAX_ITEMS = 2000
_MAX_NAME = 180
_MAX_Q = 200


def _sort_key(item):
    return (item[1], item[0])


def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError("payload must be object")
    if "companies" in payload:
        companies_raw = payload["companies"]
    else:
        companies_raw = []
    if "contacts" in payload:
        contacts_raw = payload["contacts"]
    else:
        contacts_raw = []
    if "deals" in payload:
        deals_raw = payload["deals"]
    else:
        deals_raw = []
    if "q" in payload:
        q_raw = payload["q"]
    else:
        q_raw = None
    if not isinstance(companies_raw, list):
        raise ValueError("companies must be list")
    if not isinstance(contacts_raw, list):
        raise ValueError("contacts must be list")
    if not isinstance(deals_raw, list):
        raise ValueError("deals must be list")
    if len(companies_raw) > 2000:
        raise ValueError("companies over limit")
    if len(contacts_raw) > 2000:
        raise ValueError("contacts over limit")
    if len(deals_raw) > 2000:
        raise ValueError("deals over limit")
    companies = []
    for entry in companies_raw:
        if not isinstance(entry, dict):
            raise ValueError("company must be object")
        if "pk" not in entry:
            raise ValueError("company pk missing")
        if "name" not in entry:
            raise ValueError("company name missing")
        pk = entry["pk"]
        name = entry["name"]
        if type(pk) is not int:
            raise ValueError("company pk must be int")
        if pk < 1:
            raise ValueError("company pk out of range")
        if pk > 9007199254740991:
            raise ValueError("company pk out of range")
        if not isinstance(name, str):
            raise ValueError("company name must be str")
        if len(name) < 1:
            raise ValueError("company name out of range")
        if len(name) > 180:
            raise ValueError("company name out of range")
        companies.append((pk, name))
    contacts = []
    for entry in contacts_raw:
        if not isinstance(entry, dict):
            raise ValueError("contact must be object")
        if "pk" not in entry:
            raise ValueError("contact pk missing")
        pk = entry["pk"]
        if type(pk) is not int:
            raise ValueError("contact pk must be int")
        if pk < 1:
            raise ValueError("contact pk out of range")
        if pk > 9007199254740991:
            raise ValueError("contact pk out of range")
        if "company_pk" in entry:
            cpk = entry["company_pk"]
        else:
            cpk = None
        if cpk is None:
            contacts.append((pk, None))
        else:
            if type(cpk) is not int:
                raise ValueError("contact company_pk must be int or None")
            if cpk < 1:
                raise ValueError("contact company_pk out of range")
            if cpk > 9007199254740991:
                raise ValueError("contact company_pk out of range")
            contacts.append((pk, cpk))
    deals = []
    for entry in deals_raw:
        if not isinstance(entry, dict):
            raise ValueError("deal must be object")
        if "pk" not in entry:
            raise ValueError("deal pk missing")
        pk = entry["pk"]
        if type(pk) is not int:
            raise ValueError("deal pk must be int")
        if pk < 1:
            raise ValueError("deal pk out of range")
        if pk > 9007199254740991:
            raise ValueError("deal pk out of range")
        if "company_pk" in entry:
            cpk = entry["company_pk"]
        else:
            cpk = None
        if cpk is None:
            deals.append((pk, None))
        else:
            if type(cpk) is not int:
                raise ValueError("deal company_pk must be int or None")
            if cpk < 1:
                raise ValueError("deal company_pk out of range")
            if cpk > 9007199254740991:
                raise ValueError("deal company_pk out of range")
            deals.append((pk, cpk))
    if q_raw is None:
        q_norm = ""
    elif isinstance(q_raw, str):
        q_norm = q_raw.strip()[:200]
    else:
        raise ValueError("q must be str or None")
    kept = []
    if q_norm == "":
        for item in companies:
            kept.append(item)
    else:
        qfold = q_norm.casefold()
        for item in companies:
            nm = item[1]
            if qfold in nm.casefold():
                kept.append(item)
    kept_sorted = sorted(kept, key=_sort_key)
    results = []
    for item in kept_sorted:
        c_pk = item[0]
        c_name = item[1]
        cc = 0
        for c in contacts:
            if c[1] == c_pk:
                cc = cc + 1
        dc = 0
        for d in deals:
            if d[1] == c_pk:
                dc = dc + 1
        results.append({"pk": c_pk, "name": c_name, "contact_count": cc, "deal_count": dc})
    return {"q": q_norm, "total_count": len(results), "results": results}
