# Brazilian currency input parser core.
# Pure deterministic syntax parser with no I/O.
# Accepts optional R$ prefix and BR grouping.
# Returns cents plus csv and display strings.

def _all_digits(text):
    if text == "":
        return False
    for ch in text:
        if ch < "0":
            return False
        if ch > "9":
            return False
    return True

def _is_grouped_valid(int_part):
    if int_part == "":
        return False
    for ch in int_part:
        if ch == ".":
            continue
        if ch < "0":
            return False
        if ch > "9":
            return False
    dot_found = False
    for ch in int_part:
        if ch == ".":
            dot_found = True
    if dot_found == False:
        return _all_digits(int_part)
    parts = int_part.split(".")
    first = parts[0]
    if len(first) < 1:
        return False
    if len(first) > 3:
        return False
    if _all_digits(first) == False:
        return False
    for i in range(1, len(parts)):
        part = parts[i]
        if len(part) != 3:
            return False
        if _all_digits(part) == False:
            return False
    return True

def run_feature(payload):
    if isinstance(payload, dict) == False:
        raise ValueError("payload must be object")
    if "raw" not in payload:
        raise ValueError("raw must be string")
    raw = payload["raw"]
    if isinstance(raw, str) == False:
        raise ValueError("raw must be string")
    if len(raw) > 64:
        raise ValueError("raw too long")
    trimmed = raw.strip(" \t\n\r")
    if trimmed == "":
        raise ValueError("empty input")
    if len(trimmed) >= 2:
        if trimmed[0] == "R":
            if trimmed[1] == "$":
                trimmed = trimmed[2:].strip(" \t\n\r")
                if trimmed == "":
                    raise ValueError("empty input")
    s = trimmed
    for ch in s:
        if ch == " ":
            raise ValueError("inner whitespace")
        if ch == "\t":
            raise ValueError("inner whitespace")
        if ch == "\n":
            raise ValueError("inner whitespace")
        if ch == "\r":
            raise ValueError("inner whitespace")
    for ch in s:
        if ch == ".":
            continue
        if ch == ",":
            continue
        if ch < "0":
            raise ValueError("bad character")
        if ch > "9":
            raise ValueError("bad character")
    comma_found = False
    for ch in s:
        if ch == ",":
            comma_found = True
    if comma_found:
        comma_count = 0
        for ch in s:
            if ch == ",":
                comma_count = comma_count + 1
        if comma_count != 1:
            raise ValueError("bad comma")
        comma_index = 0
        for i in range(len(s)):
            if s[i] == ",":
                comma_index = i
                break
        int_part = s[:comma_index]
        frac_part = s[comma_index + 1:]
        if len(frac_part) < 1:
            raise ValueError("bad fraction")
        if len(frac_part) > 2:
            raise ValueError("bad fraction")
        if _all_digits(frac_part) == False:
            raise ValueError("bad fraction")
        if int_part == "":
            raise ValueError("bad integer")
        if _is_grouped_valid(int_part) == False:
            raise ValueError("bad grouping")
        digits = ""
        for ch in int_part:
            if ch != ".":
                digits = digits + ch
        if digits == "":
            raise ValueError("bad integer")
        if digits == "0":
            pass
        else:
            if digits[0] < "1":
                raise ValueError("bad integer")
            if digits[0] > "9":
                raise ValueError("bad integer")
            if len(digits) > 12:
                raise ValueError("integer too long")
            if _all_digits(digits) == False:
                raise ValueError("bad integer")
        if len(frac_part) == 1:
            frac_two = frac_part + "0"
        else:
            frac_two = frac_part
        int_value = int(digits)
        frac_value = int(frac_two)
        cents = int_value * 100 + frac_value
        if cents > 99999999999999:
            raise ValueError("value too large")
        value_csv = digits + "." + frac_two
        value_display = "R$ " + digits + "," + frac_two
        return {"cents": cents, "value_csv": value_csv, "value_display": value_display}
    dot_count = 0
    for ch in s:
        if ch == ".":
            dot_count = dot_count + 1
    if dot_count > 1:
        raise ValueError("bad dot")
    if dot_count == 0:
        int_part = s
        frac_two = "00"
        if int_part == "":
            raise ValueError("bad integer")
        if _all_digits(int_part) == False:
            raise ValueError("bad integer")
        if int_part == "0":
            digits = "0"
        else:
            if int_part[0] < "1":
                raise ValueError("bad integer")
            if int_part[0] > "9":
                raise ValueError("bad integer")
            if len(int_part) > 12:
                raise ValueError("integer too long")
            if _all_digits(int_part) == False:
                raise ValueError("bad integer")
            digits = int_part
        int_value = int(digits)
        frac_value = int(frac_two)
        cents = int_value * 100 + frac_value
        if cents > 99999999999999:
            raise ValueError("value too large")
        value_csv = digits + "." + frac_two
        value_display = "R$ " + digits + "," + frac_two
        return {"cents": cents, "value_csv": value_csv, "value_display": value_display}
    dot_index = 0
    for i in range(len(s)):
        if s[i] == ".":
            dot_index = i
            break
    int_part = s[:dot_index]
    frac_part = s[dot_index + 1:]
    if len(frac_part) < 1:
        raise ValueError("bad fraction")
    if len(frac_part) > 2:
        raise ValueError("bad fraction")
    if _all_digits(frac_part) == False:
        raise ValueError("bad fraction")
    if int_part == "":
        raise ValueError("bad integer")
    if _all_digits(int_part) == False:
        raise ValueError("bad integer")
    if int_part == "0":
        digits = "0"
    else:
        if int_part[0] < "1":
            raise ValueError("bad integer")
        if int_part[0] > "9":
            raise ValueError("bad integer")
        if len(int_part) > 12:
            raise ValueError("integer too long")
        if _all_digits(int_part) == False:
            raise ValueError("bad integer")
        digits = int_part
    if len(frac_part) == 1:
        frac_two = frac_part + "0"
    else:
        frac_two = frac_part
    int_value = int(digits)
    frac_value = int(frac_two)
    cents = int_value * 100 + frac_value
    if cents > 99999999999999:
        raise ValueError("value too large")
    value_csv = digits + "." + frac_two
    value_display = "R$ " + digits + "," + frac_two
    return {"cents": cents, "value_csv": value_csv, "value_display": value_display}
