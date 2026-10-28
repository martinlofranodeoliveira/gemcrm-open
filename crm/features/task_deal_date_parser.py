# Task and deal date parser core for Task due_date and Deal expected_close input.
# Pure deterministic parser accepting ISO YYYY-MM-DD and BR D/M/YYYY.
_MAX_RAW_LENGTH = 5000
_MAX_NORMALIZED_LENGTH = 100
_MIN_YEAR = 1
_MAX_YEAR = 9999
_MIN_MONTH = 1
_MAX_MONTH = 12
_MIN_DAY = 1
_ISO_LENGTH = 10
def _is_ws(ch):
    if ch == " ":
        return True
    if ch == "\t":
        return True
    if ch == "\n":
        return True
    if ch == "\r":
        return True
    return False
def _all_digits(s):
    if len(s) == 0:
        return False
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c < "0":
            return False
        if c > "9":
            return False
        i = i + 1
    return True
def _is_leap_year(y):
    if y % 400 == 0:
        return True
    if y % 100 == 0:
        return False
    if y % 4 == 0:
        return True
    return False
def _days_in_month(y, m):
    if m == 1:
        return 31
    if m == 2:
        if _is_leap_year(y):
            return 29
        return 28
    if m == 3:
        return 31
    if m == 4:
        return 30
    if m == 5:
        return 31
    if m == 6:
        return 30
    if m == 7:
        return 31
    if m == 8:
        return 31
    if m == 9:
        return 30
    if m == 10:
        return 31
    if m == 11:
        return 30
    if m == 12:
        return 31
    return 0
def _pad2(n):
    s = str(n)
    if len(s) == 1:
        return "0" + s
    return s
def _pad4(n):
    s = str(n)
    if len(s) == 1:
        return "000" + s
    if len(s) == 2:
        return "00" + s
    if len(s) == 3:
        return "0" + s
    return s
def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError("payload must be object")
    if "text" not in payload:
        raise ValueError("text is required")
    text = payload["text"]
    if not isinstance(text, str):
        raise ValueError("text must be str")
    if len(text) > _MAX_RAW_LENGTH:
        raise ValueError("text too long")
    start = 0
    end = len(text)
    while start < end:
        c = text[start]
        if _is_ws(c):
            start = start + 1
        else:
            break
    while end > start:
        c2 = text[end - 1]
        if _is_ws(c2):
            end = end - 1
        else:
            break
    normalized = text[start:end]
    if len(normalized) == 0:
        raise ValueError("text must not be empty")
    if len(normalized) > _MAX_NORMALIZED_LENGTH:
        raise ValueError("text too long")
    has_slash = False
    k = 0
    nk = len(normalized)
    while k < nk:
        if normalized[k] == "/":
            has_slash = True
            break
        k = k + 1
    if has_slash:
        first = -1
        second = -1
        j = 0
        nlen = len(normalized)
        while j < nlen:
            if normalized[j] == "/":
                if first == -1:
                    first = j
                else:
                    if second == -1:
                        second = j
                    else:
                        raise ValueError("invalid br shape")
            j = j + 1
        if first == -1:
            raise ValueError("invalid br shape")
        if second == -1:
            raise ValueError("invalid br shape")
        day_str = normalized[0:first]
        month_str = normalized[first + 1:second]
        year_str = normalized[second + 1:nlen]
        if len(day_str) < 1:
            raise ValueError("invalid br shape")
        if len(day_str) > 2:
            raise ValueError("invalid br shape")
        if len(month_str) < 1:
            raise ValueError("invalid br shape")
        if len(month_str) > 2:
            raise ValueError("invalid br shape")
        if len(year_str) != 4:
            raise ValueError("invalid br shape")
        if not _all_digits(day_str):
            raise ValueError("invalid br shape")
        if not _all_digits(month_str):
            raise ValueError("invalid br shape")
        if not _all_digits(year_str):
            raise ValueError("invalid br shape")
        day = int(day_str)
        month = int(month_str)
        year = int(year_str)
        input_format = "br"
    else:
        if len(normalized) != _ISO_LENGTH:
            raise ValueError("invalid iso shape")
        if normalized[4] != "-":
            raise ValueError("invalid iso shape")
        if normalized[7] != "-":
            raise ValueError("invalid iso shape")
        year_str2 = normalized[0:4]
        month_str2 = normalized[5:7]
        day_str2 = normalized[8:10]
        if not _all_digits(year_str2):
            raise ValueError("invalid iso shape")
        if not _all_digits(month_str2):
            raise ValueError("invalid iso shape")
        if not _all_digits(day_str2):
            raise ValueError("invalid iso shape")
        year = int(year_str2)
        month = int(month_str2)
        day = int(day_str2)
        input_format = "iso"
    if year < _MIN_YEAR:
        raise ValueError("invalid year")
    if year > _MAX_YEAR:
        raise ValueError("invalid year")
    if month < _MIN_MONTH:
        raise ValueError("invalid month")
    if month > _MAX_MONTH:
        raise ValueError("invalid month")
    max_day = _days_in_month(year, month)
    if day < _MIN_DAY:
        raise ValueError("invalid day")
    if day > max_day:
        raise ValueError("invalid day")
    iso_date = _pad4(year) + "-" + _pad2(month) + "-" + _pad2(day)
    display_br = _pad2(day) + "/" + _pad2(month) + "/" + _pad4(year)
    return {"iso_date": iso_date, "year": year, "month": month, "day": day, "input_format": input_format, "display_br": display_br}
