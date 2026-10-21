"""Import company name resolver core - pure snapshot guard."""
_MAX_COMPANIES = 2000
_MAX_ROWS = 500
_MAX_NAME_LEN = 180
_MIN_PK = 1
_MIN_LINE = 2
def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError("payload must be object")
    if "companies" in payload:
        companies = payload["companies"]
    else:
        companies = []
    if "rows" in payload:
        rows = payload["rows"]
    else:
        rows = []
    if not isinstance(companies, list):
        raise ValueError("companies must be list")
    if not isinstance(rows, list):
        raise ValueError("rows must be list")
    if len(companies) > _MAX_COMPANIES:
        raise ValueError("too many companies")
    if len(rows) > _MAX_ROWS:
        raise ValueError("too many rows")
    first_pk_by_name = {}
    ambiguous_by_name = {}
    for entry in companies:
        if not isinstance(entry, dict):
            raise ValueError("company entry must be object")
        if "pk" not in entry:
            raise ValueError("company pk missing")
        if "name" not in entry:
            raise ValueError("company name missing")
        pk = entry["pk"]
        name = entry["name"]
        if type(pk) is not int:
            raise ValueError("company pk must be int")
        if pk < _MIN_PK:
            raise ValueError("company pk out of range")
        if not isinstance(name, str):
            raise ValueError("company name must be str")
        if len(name) < 1:
            raise ValueError("company name empty")
        if len(name) > _MAX_NAME_LEN:
            raise ValueError("company name too long")
        if name in first_pk_by_name:
            if first_pk_by_name[name] != pk:
                ambiguous_by_name[name] = True
        else:
            first_pk_by_name[name] = pk
    seen_lines = {}
    for entry in rows:
        if not isinstance(entry, dict):
            raise ValueError("row entry must be object")
        if "line" not in entry:
            raise ValueError("row line missing")
        if "company" not in entry:
            raise ValueError("row company missing")
        line = entry["line"]
        company = entry["company"]
        if type(line) is not int:
            raise ValueError("row line must be int")
        if line < _MIN_LINE:
            raise ValueError("row line out of range")
        if not isinstance(company, str):
            raise ValueError("row company must be str")
        if len(company) > _MAX_NAME_LEN:
            raise ValueError("row company too long")
        if line in seen_lines:
            raise ValueError("duplicate line")
        seen_lines[line] = True
    results = []
    resolved_count = 0
    empty_count = 0
    missing_count = 0
    ambiguous_count = 0
    for entry in rows:
        line = entry["line"]
        company = entry["company"]
        company_copy = "%s" % company
        if company == "":
            status = "empty"
            company_pk = None
            empty_count = empty_count + 1
        else:
            if company in first_pk_by_name:
                if company in ambiguous_by_name:
                    status = "ambiguous"
                    company_pk = None
                    ambiguous_count = ambiguous_count + 1
                else:
                    status = "resolved"
                    company_pk = first_pk_by_name[company]
                    resolved_count = resolved_count + 1
            else:
                status = "missing"
                company_pk = None
                missing_count = missing_count + 1
        results = results + [{"line": line, "company": company_copy, "status": status, "company_pk": company_pk}]
    total_count = len(rows)
    if missing_count == 0:
        if ambiguous_count == 0:
            can_import = True
        else:
            can_import = False
    else:
        can_import = False
    return {"total_count": total_count, "resolved_count": resolved_count, "empty_count": empty_count, "missing_count": missing_count, "ambiguous_count": ambiguous_count, "can_import": can_import, "results": results}
