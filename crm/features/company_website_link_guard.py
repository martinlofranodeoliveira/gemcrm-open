def _trim_ascii(value):
    return value.strip(" \t\n\r")


def _has_http_scheme(trimmed):
    lowered = trimmed.lower()
    if lowered.startswith("http://"):
        return True
    if lowered.startswith("https://"):
        return True
    return False


def _scheme_length(trimmed):
    lowered = trimmed.lower()
    if lowered.startswith("https://"):
        return 8
    return 7


def _extract_host(trimmed, start):
    end = len(trimmed)
    for i in range(start, len(trimmed)):
        c = trimmed[i]
        if c == "/":
            end = i
            break
        if c == "?":
            end = i
            break
        if c == "#":
            end = i
            break
    return trimmed[start:end]


def _host_is_bad(host):
    if " " in host:
        return True
    if "\t" in host:
        return True
    if "\n" in host:
        return True
    if "\r" in host:
        return True
    if "<" in host:
        return True
    if ">" in host:
        return True
    if '"' in host:
        return True
    if "'" in host:
        return True
    if "`" in host:
        return True
    if "\\" in host:
        return True
    return False


def run_feature(payload):
    if payload is None:
        raise ValueError("payload must be dict")
    if not isinstance(payload, dict):
        raise ValueError("payload must be dict")
    if "websites" in payload:
        websites = payload["websites"]
    else:
        websites = []
    if websites is None:
        raise ValueError("websites must be list")
    if not isinstance(websites, list):
        raise ValueError("websites must be list")
    if len(websites) > 20:
        raise ValueError("too many websites")
    for index in range(len(websites)):
        item = websites[index]
        if not isinstance(item, str):
            raise ValueError("website must be str")
        if len(item) > 500:
            raise ValueError("website too long")
    results = []
    allowed_count = 0
    for index in range(len(websites)):
        website = websites[index]
        trimmed = _trim_ascii(website)
        if trimmed == "":
            entry = {"index": index, "website": website, "trimmed": trimmed, "kind": "blank", "allowed": True, "href": None, "display_host": "", "reasons": []}
            results.append(entry)
            allowed_count = allowed_count + 1
        else:
            has_scheme = _has_http_scheme(trimmed)
            has_space = False
            if " " in trimmed:
                has_space = True
            if "\t" in trimmed:
                has_space = True
            if "\n" in trimmed:
                has_space = True
            if "\r" in trimmed:
                has_space = True
            has_unsafe = False
            if "<" in trimmed:
                has_unsafe = True
            if ">" in trimmed:
                has_unsafe = True
            if '"' in trimmed:
                has_unsafe = True
            if "'" in trimmed:
                has_unsafe = True
            if "`" in trimmed:
                has_unsafe = True
            if "\\" in trimmed:
                has_unsafe = True
            missing = False
            host = ""
            if has_scheme:
                start = _scheme_length(trimmed)
                host = _extract_host(trimmed, start)
                if host == "":
                    missing = True
                else:
                    if _host_is_bad(host):
                        missing = True
            reasons = []
            if not has_scheme:
                reasons.append("unsafe_scheme")
            if has_space:
                reasons.append("contains_space")
            if has_unsafe:
                reasons.append("unsafe_chars")
            if missing:
                reasons.append("missing_host")
            if len(reasons) == 0:
                display = host.lower()
                entry = {"index": index, "website": website, "trimmed": trimmed, "kind": "link", "allowed": True, "href": trimmed, "display_host": display, "reasons": []}
                results.append(entry)
                allowed_count = allowed_count + 1
            else:
                entry = {"index": index, "website": website, "trimmed": trimmed, "kind": "link", "allowed": False, "href": None, "display_host": "", "reasons": reasons}
                results.append(entry)
    total_count = len(websites)
    blocked_count = total_count - allowed_count
    return {"total_count": total_count, "allowed_count": allowed_count, "blocked_count": blocked_count, "results": results}
