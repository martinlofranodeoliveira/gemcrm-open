import re

_NAME_REQUIRED = "name is required"
_NAME_MUST_BE_STRING = "name must be a string"
_NAME_TOO_LONG = "name must be at most 180 characters"
_WEBSITE_INVALID = "website must be a valid URL or empty"
_NOTES_MUST_BE_STRING = "notes must be a string"
_NOTES_TOO_LONG = "notes must be at most 10000 characters"
_WEBSITE_PATTERN = "^https?://[^\\s]+\\.[^\\s]+$"
_TRIM_CHARS = " \t\n\r"
_PAYLOAD_ERROR = "payload must be an object"


def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError(_PAYLOAD_ERROR)
    errors = {}
    normalized_name = ""
    normalized_website = ""
    normalized_notes = ""
    if "name" not in payload:
        errors["name"] = _NAME_REQUIRED
    else:
        raw_name = payload["name"]
        if raw_name is None:
            errors["name"] = _NAME_REQUIRED
        elif not isinstance(raw_name, str):
            errors["name"] = _NAME_MUST_BE_STRING
        else:
            trimmed_name = raw_name.strip(_TRIM_CHARS)
            if trimmed_name == "":
                errors["name"] = _NAME_REQUIRED
            elif len(trimmed_name) > 180:
                errors["name"] = _NAME_TOO_LONG
            else:
                normalized_name = trimmed_name
    if "website" not in payload:
        normalized_website = ""
    else:
        raw_website = payload["website"]
        if raw_website is None:
            normalized_website = ""
        elif not isinstance(raw_website, str):
            errors["website"] = _WEBSITE_INVALID
        else:
            trimmed_website = raw_website.strip(_TRIM_CHARS)
            if trimmed_website == "":
                normalized_website = ""
            elif len(trimmed_website) > 200:
                errors["website"] = _WEBSITE_INVALID
            elif re.match(_WEBSITE_PATTERN, trimmed_website) is None:
                errors["website"] = _WEBSITE_INVALID
            else:
                normalized_website = trimmed_website
    if "notes" not in payload:
        normalized_notes = ""
    else:
        raw_notes = payload["notes"]
        if raw_notes is None:
            normalized_notes = ""
        elif not isinstance(raw_notes, str):
            errors["notes"] = _NOTES_MUST_BE_STRING
        elif len(raw_notes) > 10000:
            errors["notes"] = _NOTES_TOO_LONG
        else:
            normalized_notes = raw_notes
    if errors == {}:
        normalized = {}
        normalized["name"] = normalized_name
        normalized["website"] = normalized_website
        normalized["notes"] = normalized_notes
        result = {}
        result["valid"] = True
        result["errors"] = {}
        result["normalized"] = normalized
        return result
    result = {}
    result["valid"] = False
    result["errors"] = errors
    result["normalized"] = None
    return result
