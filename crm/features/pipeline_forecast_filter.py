import re

_VALUE_PATTERN = "^(0|[1-9][0-9]*)(\\.[0-9]{1,2})?$"
_MAX_CENTS = 99999999999999
_MAX_DEALS = 5000
_STAGES = ("new", "qualified", "proposal", "won", "lost")


def _is_leap_year(year):
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)


def _is_valid_calendar_date(text):
    if not isinstance(text, str):
        return False
    if len(text) != 10:
        return False
    if text[4] != "-":
        return False
    if text[7] != "-":
        return False
    year_s = text[0:4]
    month_s = text[5:7]
    day_s = text[8:10]
    if not year_s.isdigit():
        return False
    if not month_s.isdigit():
        return False
    if not day_s.isdigit():
        return False
    year = int(year_s)
    month = int(month_s)
    day = int(day_s)
    if year < 1:
        return False
    if year > 9999:
        return False
    if month < 1:
        return False
    if month > 12:
        return False
    if day < 1:
        return False
    if month == 2:
        if _is_leap_year(year):
            limit = 29
        else:
            limit = 28
        if day > limit:
            return False
    else:
        if month == 4 or month == 6 or month == 9 or month == 11:
            limit = 30
        else:
            limit = 31
        if day > limit:
            return False
    return True


def _normalize_bound(value):
    if value is None:
        return None
    if isinstance(value, str):
        if value == "":
            return None
        if not _is_valid_calendar_date(value):
            raise ValueError("invalid bound date")
        return value
    raise ValueError("invalid bound date")


def _value_to_cents(text):
    if not isinstance(text, str):
        raise ValueError("invalid value")
    if re.match(_VALUE_PATTERN, text) is None:
        raise ValueError("invalid value")
    dot = text.find(".")
    if dot == -1:
        whole_s = text
        frac_s = ""
    else:
        whole_s = text[0:dot]
        frac_s = text[dot + 1:]
    whole = int(whole_s)
    if frac_s == "":
        cents = whole * 100
    else:
        if len(frac_s) == 1:
            cents = whole * 100 + int(frac_s) * 10
        else:
            cents = whole * 100 + int(frac_s)
    if cents > _MAX_CENTS:
        raise ValueError("invalid value")
    return cents


def _format_csv(cents):
    whole = cents // 100
    frac = cents % 100
    if frac < 10:
        frac_s = "0" + str(frac)
    else:
        frac_s = str(frac)
    return str(whole) + "." + frac_s


def _format_display(cents):
    whole = cents // 100
    frac = cents % 100
    if frac < 10:
        frac_s = "0" + str(frac)
    else:
        frac_s = str(frac)
    return "R$ " + str(whole) + "," + frac_s


def run_feature(payload):
    """Pure snapshot of pipeline by forecast date with per-stage totals."""
    if not isinstance(payload, dict):
        raise ValueError("invalid payload")
    if "deals" in payload:
        deals_raw = payload["deals"]
    else:
        deals_raw = []
    if "start" in payload:
        start_raw = payload["start"]
    else:
        start_raw = None
    if "end" in payload:
        end_raw = payload["end"]
    else:
        end_raw = None
    if not isinstance(deals_raw, list):
        raise ValueError("invalid deals")
    if len(deals_raw) > _MAX_DEALS:
        raise ValueError("too many deals")
    start = _normalize_bound(start_raw)
    end = _normalize_bound(end_raw)
    if start is not None:
        if end is not None:
            if start > end:
                raise ValueError("invalid interval")
    counts = {}
    totals = {}
    for s in _STAGES:
        counts[s] = 0
        totals[s] = 0
    results = []
    for raw in deals_raw:
        if not isinstance(raw, dict):
            raise ValueError("invalid deal")
        if "pk" in raw:
            pk = raw["pk"]
        else:
            raise ValueError("invalid pk")
        if type(pk) is not int:
            raise ValueError("invalid pk")
        if "title" in raw:
            title = raw["title"]
        else:
            raise ValueError("invalid title")
        if not isinstance(title, str):
            raise ValueError("invalid title")
        if "stage" in raw:
            stage = raw["stage"]
        else:
            raise ValueError("invalid stage")
        if not isinstance(stage, str):
            raise ValueError("invalid stage")
        if stage not in _STAGES:
            raise ValueError("invalid stage")
        if "value" in raw:
            value_raw = raw["value"]
        else:
            raise ValueError("invalid value")
        cents = _value_to_cents(value_raw)
        if "expected_close" in raw:
            ec_raw = raw["expected_close"]
        else:
            ec_raw = None
        if ec_raw is None:
            expected = None
        else:
            if isinstance(ec_raw, str):
                if ec_raw == "":
                    expected = None
                else:
                    if not _is_valid_calendar_date(ec_raw):
                        raise ValueError("invalid expected_close")
                    expected = ec_raw
            else:
                raise ValueError("invalid expected_close")
        keep = False
        if start is None:
            if end is None:
                keep = True
            else:
                if expected is not None:
                    if expected <= end:
                        keep = True
        else:
            if end is None:
                if expected is not None:
                    if expected >= start:
                        keep = True
            else:
                if expected is not None:
                    if expected >= start:
                        if expected <= end:
                            keep = True
        if keep:
            entry = {}
            entry["pk"] = pk
            entry["title"] = title
            entry["stage"] = stage
            entry["expected_close"] = expected
            entry["value_cents"] = cents
            entry["value_csv"] = _format_csv(cents)
            entry["value_display"] = _format_display(cents)
            results.append(entry)
            counts[stage] = counts[stage] + 1
            totals[stage] = totals[stage] + cents
    by_stage = {}
    grand_count = 0
    grand_total = 0
    for s in _STAGES:
        c = counts[s]
        t = totals[s]
        item = {}
        item["count"] = c
        item["total_cents"] = t
        item["total_csv"] = _format_csv(t)
        item["total_display"] = _format_display(t)
        by_stage[s] = item
        grand_count = grand_count + c
        grand_total = grand_total + t
    grand = {}
    grand["count"] = grand_count
    grand["total_cents"] = grand_total
    grand["total_csv"] = _format_csv(grand_total)
    grand["total_display"] = _format_display(grand_total)
    out = {}
    out["start"] = start
    out["end"] = end
    out["total_count"] = len(results)
    out["results"] = results
    out["by_stage"] = by_stage
    out["grand"] = grand
    return out
