import re
import unicodedata

_FALLBACK_BASE = "export"
_DEFAULT_EXT = "csv"
_STRIP_WS = " \t\n\r"
_NORM_FORM = "NFKD"
_MARK_CAT = "Mn"
_NON_ALNUM = "[^a-z0-9]+"
_HYPHEN = "-"
_DOT = "."
_BASE_KEY = "base"
_TAG_KEY = "tag"
_EXT_KEY = "ext"
_MAX_INPUT = 500
_BASE_LIMIT = 30
_TAG_LIMIT = 40

def _sanitize(raw, limit):
    normalized = unicodedata.normalize(_NORM_FORM, raw)
    folded = normalized.casefold()
    kept = []
    for ch in folded:
        if unicodedata.category(ch) != _MARK_CAT:
            kept.append(ch)
    joined = "".join(kept)
    hyphenated = re.sub(_NON_ALNUM, _HYPHEN, joined)
    trimmed = hyphenated.strip(_HYPHEN)
    truncated = trimmed[:limit]
    cleaned = truncated.strip(_HYPHEN)
    return cleaned

def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError("payload must be object")
    if _BASE_KEY in payload:
        base_value = payload[_BASE_KEY]
    else:
        base_value = None
    if _TAG_KEY in payload:
        tag_value = payload[_TAG_KEY]
    else:
        tag_value = None
    if _EXT_KEY in payload:
        ext_value = payload[_EXT_KEY]
    else:
        ext_value = None
    if base_value is None:
        raw_base = _FALLBACK_BASE
    else:
        if not isinstance(base_value, str):
            raise ValueError("base must be str or None")
        if len(base_value) > _MAX_INPUT:
            raise ValueError("base too long")
        stripped_base = base_value.strip(_STRIP_WS)
        if stripped_base == "":
            raw_base = _FALLBACK_BASE
        else:
            raw_base = stripped_base
    if tag_value is None:
        raw_tag = ""
    else:
        if not isinstance(tag_value, str):
            raise ValueError("tag must be str or None")
        if len(tag_value) > _MAX_INPUT:
            raise ValueError("tag too long")
        stripped_tag = tag_value.strip(_STRIP_WS)
        if stripped_tag == "":
            raw_tag = ""
        else:
            raw_tag = stripped_tag
    if ext_value is None:
        raw_ext = _DEFAULT_EXT
    else:
        if not isinstance(ext_value, str):
            raise ValueError("ext must be str or None")
        stripped_ext = ext_value.strip(_STRIP_WS)
        if stripped_ext.casefold() != _DEFAULT_EXT:
            raise ValueError("unsupported ext")
        raw_ext = _DEFAULT_EXT
    base_slug = _sanitize(raw_base, _BASE_LIMIT)
    if base_slug == "":
        base_slug = _FALLBACK_BASE
    if raw_tag == "":
        tag_slug = ""
    else:
        tag_slug = _sanitize(raw_tag, _TAG_LIMIT)
    if tag_slug == "":
        filename = base_slug + _DOT + raw_ext
    else:
        filename = base_slug + _HYPHEN + tag_slug + _DOT + raw_ext
    result = {"filename": filename, "base_slug": base_slug, "tag_slug": tag_slug, "ext": raw_ext}
    return result
