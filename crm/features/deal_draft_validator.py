STAGES = ("new", "qualified", "proposal", "won", "lost")

MAX_CENTS = 99999999999999

MAX_PK = 9007199254740991

MAX_TITLE = 180


def _is_leap_year(year):
    if year % 400 == 0:
        return True
    if year % 100 == 0:
        return False
    if year % 4 == 0:
        return True
    return False


def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    errors = {}
    title_val = None
    if "title" not in payload:
        errors["title"] = "title is required"
    else:
        raw_title = payload["title"]
        if raw_title is None:
            errors["title"] = "title is required"
        elif not isinstance(raw_title, str):
            errors["title"] = "title must be a string"
        else:
            trimmed = raw_title.strip(" \t\n\r")
            if trimmed == "":
                errors["title"] = "title is required"
            elif len(trimmed) > MAX_TITLE:
                errors["title"] = "title must be at most 180 characters"
            else:
                title_val = trimmed
    if "value" not in payload:
        raw_value = "0.00"
    else:
        raw_value = payload["value"]
    value_str = None
    value_cents = None
    if not isinstance(raw_value, str):
        errors["value"] = "value must be a decimal string"
    elif raw_value == "":
        errors["value"] = "value must be a decimal string"
    else:
        dot_count = raw_value.count(".")
        if dot_count > 1:
            errors["value"] = "value must be a decimal string"
        else:
            if dot_count == 1:
                parts = raw_value.split(".")
                int_part = parts[0]
                frac_part = parts[1]
            else:
                int_part = raw_value
                frac_part = None
            int_ok = False
            if int_part == "0":
                int_ok = True
            elif len(int_part) > 0 and int_part[0] in "123456789":
                digits_ok = True
                for ch in int_part:
                    if ch not in "0123456789":
                        digits_ok = False
                if digits_ok:
                    int_ok = True
            frac_ok = False
            if frac_part is None:
                frac_ok = True
            elif len(frac_part) >= 1 and len(frac_part) <= 2:
                f_ok = True
                for ch in frac_part:
                    if ch not in "0123456789":
                        f_ok = False
                if f_ok:
                    frac_ok = True
            if not int_ok or not frac_ok:
                errors["value"] = "value must be a decimal string"
            else:
                int_num = int(int_part)
                if frac_part is None:
                    frac_num = 0
                    frac_two = "00"
                elif len(frac_part) == 1:
                    frac_num = int(frac_part) * 10
                    frac_two = frac_part + "0"
                else:
                    frac_num = int(frac_part)
                    frac_two = frac_part
                total = int_num * 100 + frac_num
                if total > MAX_CENTS:
                    errors["value"] = "value is too large"
                else:
                    value_str = int_part + "." + frac_two
                    value_cents = total
    stage_val = None
    if "stage" not in payload:
        stage_val = "new"
    else:
        raw_stage = payload["stage"]
        if not isinstance(raw_stage, str):
            errors["stage"] = "stage must be one of new, qualified, proposal, won, lost"
        elif raw_stage not in STAGES:
            errors["stage"] = "stage must be one of new, qualified, proposal, won, lost"
        else:
            stage_val = raw_stage
    exp_val = None
    if "expected_close" not in payload:
        exp_val = None
    else:
        raw_exp = payload["expected_close"]
        if raw_exp is None:
            exp_val = None
        elif isinstance(raw_exp, str) and raw_exp == "":
            exp_val = None
        elif not isinstance(raw_exp, str):
            errors["expected_close"] = "expected_close must be YYYY-MM-DD valid calendar date"
        elif len(raw_exp) != 10:
            errors["expected_close"] = "expected_close must be YYYY-MM-DD valid calendar date"
        elif raw_exp[4] != "-" or raw_exp[7] != "-":
            errors["expected_close"] = "expected_close must be YYYY-MM-DD valid calendar date"
        else:
            y_s = raw_exp[0:4]
            m_s = raw_exp[5:7]
            d_s = raw_exp[8:10]
            if not y_s.isdigit() or not m_s.isdigit() or not d_s.isdigit():
                errors["expected_close"] = "expected_close must be YYYY-MM-DD valid calendar date"
            else:
                y = int(y_s)
                m = int(m_s)
                d = int(d_s)
                if m < 1 or m > 12:
                    errors["expected_close"] = "expected_close must be YYYY-MM-DD valid calendar date"
                else:
                    if m == 1 or m == 3 or m == 5 or m == 7 or m == 8 or m == 10 or m == 12:
                        max_day = 31
                    elif m == 4 or m == 6 or m == 9 or m == 11:
                        max_day = 30
                    else:
                        if _is_leap_year(y):
                            max_day = 29
                        else:
                            max_day = 28
                    if d < 1 or d > max_day:
                        errors["expected_close"] = "expected_close must be YYYY-MM-DD valid calendar date"
                    else:
                        exp_val = raw_exp
    comp_val = None
    if "company_pk" not in payload:
        comp_val = None
    else:
        raw_comp = payload["company_pk"]
        if raw_comp is None:
            comp_val = None
        elif type(raw_comp) is bool:
            errors["company_pk"] = "company_pk must be an integer 1 to 9007199254740991 or null"
        elif type(raw_comp) is not int:
            errors["company_pk"] = "company_pk must be an integer 1 to 9007199254740991 or null"
        elif raw_comp < 1 or raw_comp > MAX_PK:
            errors["company_pk"] = "company_pk must be an integer 1 to 9007199254740991 or null"
        else:
            comp_val = raw_comp
    cont_val = None
    if "contact_pk" not in payload:
        cont_val = None
    else:
        raw_cont = payload["contact_pk"]
        if raw_cont is None:
            cont_val = None
        elif type(raw_cont) is bool:
            errors["contact_pk"] = "contact_pk must be an integer 1 to 9007199254740991 or null"
        elif type(raw_cont) is not int:
            errors["contact_pk"] = "contact_pk must be an integer 1 to 9007199254740991 or null"
        elif raw_cont < 1 or raw_cont > MAX_PK:
            errors["contact_pk"] = "contact_pk must be an integer 1 to 9007199254740991 or null"
        else:
            cont_val = raw_cont
    if errors != {}:
        return {"valid": False, "errors": errors, "normalized": None}
    normalized = {"title": title_val, "value": value_str, "value_cents": value_cents, "stage": stage_val, "expected_close": exp_val, "company_pk": comp_val, "contact_pk": cont_val}
    return {"valid": True, "errors": {}, "normalized": normalized}
