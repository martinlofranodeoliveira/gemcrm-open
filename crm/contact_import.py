import csv
import io


ALLOWED_HEADERS = {"name", "email", "phone", "company", "notes"}


def _validate_email(email):
    if not email:
        return True

    if email.count("@") != 1:
        return False

    local_part, domain = email.split("@", 1)
    if not local_part or not domain:
        return False

    if any(char.isspace() for char in email):
        return False

    labels = domain.split(".")
    if len(labels) < 2:
        return False

    return all(label for label in labels)


def _normalize_header(header):
    return header.strip().lower()


def _is_blank_row(row):
    return not row or all(not value.strip() for value in row)


def parse_contacts(text: str, max_rows: int = 500) -> dict:
    if not isinstance(text, str):
        raise ValueError("text must be a string")

    if isinstance(max_rows, bool) or not isinstance(max_rows, int) or max_rows <= 0:
        raise ValueError("max_rows must be a positive integer")

    text = text.lstrip("\ufeff")

    rows = []
    errors = []
    header = None
    header_line = 1
    nonblank_count = 0

    reader = csv.reader(io.StringIO(text), strict=True)

    try:
        for row in reader:
            line = reader.line_num

            if header is None:
                header = [_normalize_header(value) for value in row]

                if not header:
                    errors.append({"line": header_line, "message": "Header is required"})
                    return {"rows": rows, "errors": errors, "valid": False}

                if "name" not in header:
                    errors.append({"line": header_line, "message": "Header must include name"})
                    return {"rows": rows, "errors": errors, "valid": False}

                unknown_headers = [value for value in header if value not in ALLOWED_HEADERS]
                if unknown_headers:
                    errors.append({"line": header_line, "message": "Unknown header column"})
                    return {"rows": rows, "errors": errors, "valid": False}

                duplicate_headers = []
                seen = set()
                for value in header:
                    if value in seen:
                        duplicate_headers.append(value)
                    seen.add(value)

                if duplicate_headers:
                    errors.append({"line": header_line, "message": "Duplicate header column"})
                    return {"rows": rows, "errors": errors, "valid": False}

                continue

            if _is_blank_row(row):
                continue

            nonblank_count += 1
            if nonblank_count > max_rows:
                errors.append({"line": line, "message": "Row limit exceeded"})
                break

            if len(row) != len(header):
                errors.append({"line": line, "message": "Row width mismatch"})
                continue

            values = {key: value.strip() for key, value in zip(header, row)}

            if not values.get("name"):
                errors.append({"line": line, "message": "Name is required"})
                continue

            if not _validate_email(values.get("email", "")):
                errors.append({"line": line, "message": "Invalid email"})
                continue

            rows.append({
                "line": line,
                "name": values["name"],
                "email": values.get("email", ""),
                "phone": values.get("phone", ""),
                "company": values.get("company", ""),
                "notes": values.get("notes", ""),
            })

    except csv.Error:
        errors.append({"line": max(1, reader.line_num), "message": "Malformed CSV"})

    if header is None:
        errors.append({"line": 1, "message": "Header is required"})

    return {"rows": rows, "errors": errors, "valid": not errors}
