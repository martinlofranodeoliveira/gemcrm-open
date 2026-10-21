PER_PAGE = 50
MAX_CONTACTS = 2000
MAX_Q_CHARS = 200
MAX_PK_VALUE = 9007199254740991

def _is_ascii_digits(s):
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

def _sort_key(c):
    return (c["name"], c["pk"])

def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError("payload")
    if "contacts" in payload:
        contacts = payload["contacts"]
    else:
        contacts = []
    if "q" in payload:
        q_raw = payload["q"]
    else:
        q_raw = None
    if "page" in payload:
        page_raw = payload["page"]
    else:
        page_raw = None
    if not isinstance(contacts, list):
        raise ValueError("contacts")
    if len(contacts) > MAX_CONTACTS:
        raise ValueError("contacts")
    if q_raw is not None:
        if not isinstance(q_raw, str):
            raise ValueError("q")
    if page_raw is None:
        pass
    elif type(page_raw) is int:
        pass
    elif isinstance(page_raw, str):
        pass
    else:
        raise ValueError("page")
    i = 0
    n = len(contacts)
    while i < n:
        c = contacts[i]
        if not isinstance(c, dict):
            raise ValueError("contact")
        if "pk" not in c:
            raise ValueError("pk")
        if "name" not in c:
            raise ValueError("name")
        if "email" not in c:
            raise ValueError("email")
        if "phone" not in c:
            raise ValueError("phone")
        if "company" not in c:
            raise ValueError("company")
        pk = c["pk"]
        name = c["name"]
        email = c["email"]
        phone = c["phone"]
        company = c["company"]
        if type(pk) is not int:
            raise ValueError("pk")
        if pk < 1 or pk > MAX_PK_VALUE:
            raise ValueError("pk")
        if not isinstance(name, str):
            raise ValueError("name")
        if len(name) < 1 or len(name) > 180:
            raise ValueError("name")
        if not isinstance(email, str):
            raise ValueError("email")
        if len(email) > 254:
            raise ValueError("email")
        if not isinstance(phone, str):
            raise ValueError("phone")
        if len(phone) > 40:
            raise ValueError("phone")
        if not isinstance(company, str):
            raise ValueError("company")
        if len(company) > 180:
            raise ValueError("company")
        i = i + 1
    if q_raw is None:
        q = ""
    else:
        q = q_raw.strip()
        q = q[:MAX_Q_CHARS]
    kept = []
    if q == "":
        j = 0
        while j < len(contacts):
            kept.append(contacts[j])
            j = j + 1
    else:
        qf = q.casefold()
        j = 0
        while j < len(contacts):
            c = contacts[j]
            nf = c["name"].casefold()
            ef = c["email"].casefold()
            pf = c["phone"].casefold()
            cf = c["company"].casefold()
            if qf in nf or qf in ef or qf in pf or qf in cf:
                kept.append(c)
            j = j + 1
    ordered = sorted(kept, key=_sort_key)
    total_count = len(ordered)
    if total_count == 0:
        total_pages = 1
    else:
        total_pages = (total_count + 49) // PER_PAGE
    if page_raw is None:
        parsed = 1
    elif type(page_raw) is int:
        parsed = page_raw
    else:
        s = page_raw.strip()
        if s == "":
            parsed = 1
        else:
            body = s
            if s[0] == "+" or s[0] == "-":
                body = s[1:]
            if _is_ascii_digits(body):
                parsed = int(s)
            else:
                parsed = 1
    if parsed >= 1 and parsed <= total_pages:
        page_effective = parsed
    else:
        page_effective = total_pages
    start = (page_effective - 1) * PER_PAGE
    end = start + PER_PAGE
    results = []
    k = start
    while k < end and k < total_count:
        src = ordered[k]
        results.append({"pk": src["pk"], "name": src["name"], "email": src["email"], "phone": src["phone"], "company": src["company"]})
        k = k + 1
    if page_effective > 1:
        has_previous = True
        prev_page = page_effective - 1
    else:
        has_previous = False
        prev_page = None
    if page_effective < total_pages:
        has_next = True
        next_page = page_effective + 1
    else:
        has_next = False
        next_page = None
    return {"q": q, "page_effective": page_effective, "per_page": PER_PAGE, "total_count": total_count, "total_pages": total_pages, "has_previous": has_previous, "has_next": has_next, "prev_page": prev_page, "next_page": next_page, "results": results}
