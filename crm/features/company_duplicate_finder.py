_MAX_COMPANIES = 5000
_MAX_NAME_LENGTH = 180
_MIN_PK = 1
_MAX_PK = 9007199254740991
_STRIP_CHARS = " \t\n\r"


def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError("payload must be object")
    if "companies" in payload:
        companies = payload["companies"]
    else:
        companies = []
    if not isinstance(companies, list):
        raise ValueError("companies must be list")
    if len(companies) > _MAX_COMPANIES:
        raise ValueError("companies too large")
    seen = {}
    grouped = {}
    for entry in companies:
        if not isinstance(entry, dict):
            raise ValueError("entry must be object")
        if "pk" not in entry:
            raise ValueError("pk missing")
        if "name" not in entry:
            raise ValueError("name missing")
        pk = entry["pk"]
        name = entry["name"]
        if type(pk) is not int:
            raise ValueError("pk must be int")
        if pk < _MIN_PK:
            raise ValueError("pk out of range")
        if pk > _MAX_PK:
            raise ValueError("pk out of range")
        if type(name) is not str:
            raise ValueError("name must be str")
        if len(name) > _MAX_NAME_LENGTH:
            raise ValueError("name too long")
        trimmed = name.strip(_STRIP_CHARS)
        if len(trimmed) == 0:
            raise ValueError("name empty")
        key = trimmed.casefold()
        if pk in seen:
            raise ValueError("duplicate pk")
        seen[pk] = True
        item = {"pk": pk, "name": name}
        if key in grouped:
            grouped[key].append(item)
        else:
            grouped[key] = [item]
    keys = []
    for k in grouped:
        if len(grouped[k]) > 1:
            keys.append(k)
    keys.sort()
    groups = []
    for k in keys:
        members = grouped[k]
        pairs = []
        for m in members:
            pairs.append((m["pk"], m["name"]))
        pairs.sort()
        ordered = []
        for p in pairs:
            ordered.append({"pk": p[0], "name": p[1]})
        groups.append({"key": k, "count": len(ordered), "companies": ordered})
    return {"group_count": len(groups), "groups": groups}
