"""Detect duplicate contact emails before import.

This module provides a pure helper for callers that already have parsed contact
rows and the current owner's existing email addresses. It does not query users,
verify ownership, enforce uniqueness in a database, import contacts, or replace
transactional write-time checks.

Normalization policy:
- Emails are normalized with strip().casefold().
- Normalized blank emails are ignored.
- Nonblank emails must contain exactly one @, a nonempty local part, no internal
  whitespace, and at least two nonempty dot-separated domain labels.
- Dots, plus suffixes, and provider-specific aliases are not merged or removed.

Caller ownership responsibility:
- Callers must pass only the current owner's existing emails.
- Direct composition with parse_contacts is expected: pass parse_contacts rows
  and the caller-provided existing email list to detect_duplicate_emails.

The helper returns fresh conflict dictionaries only for conflicting nonblank
import rows. It never mutates inputs and never returns original row dictionaries
or unrelated fields.
"""


def _normalize_email(email):
    return email.strip().casefold()


def _is_valid_nonblank_email(email):
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


def _validate_positive_int(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(name + " must be a positive integer")


def detect_duplicate_emails(
    rows: list[dict],
    existing_emails: list[str],
    *,
    max_rows: int = 500,
    max_existing: int = 20000,
) -> list[dict]:
    """Return fresh conflict dictionaries for duplicate import rows.

    Each returned dictionary contains exactly:
    - line: original import row line number
    - email: normalized import email
    - existing: bool membership in supplied existing_emails
    - previous_line: first previous matching import row line, or None
    """
    if not isinstance(rows, list):
        raise ValueError("rows must be a list")

    if not isinstance(existing_emails, list):
        raise ValueError("existing_emails must be a list")

    _validate_positive_int(max_rows, "max_rows")
    _validate_positive_int(max_existing, "max_existing")

    if len(rows) > max_rows:
        raise ValueError("rows exceed max_rows")

    if len(existing_emails) > max_existing:
        raise ValueError("existing_emails exceed max_existing")

    normalized_existing = set()
    for existing_email in existing_emails:
        if not isinstance(existing_email, str):
            raise ValueError("existing_emails must contain strings")

        normalized = _normalize_email(existing_email)
        if not normalized:
            continue

        if not _is_valid_nonblank_email(normalized):
            raise ValueError("existing_emails contains an invalid email")

        normalized_existing.add(normalized)

    seen_lines = set()
    validated_rows = []

    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("rows must contain dictionaries")

        line = row.get("line")
        if isinstance(line, bool) or not isinstance(line, int) or line < 2:
            raise ValueError("rows must contain valid line numbers")

        if line in seen_lines:
            raise ValueError("rows must contain unique line numbers")

        seen_lines.add(line)

        email = row.get("email")
        if not isinstance(email, str):
            raise ValueError("rows must contain string emails")

        normalized = _normalize_email(email)
        if normalized and not _is_valid_nonblank_email(normalized):
            raise ValueError("rows contain an invalid email")

        validated_rows.append((line, normalized))

    first_seen_line = {}
    conflicts = []

    for line, normalized in validated_rows:
        if not normalized:
            continue

        existing = normalized in normalized_existing
        previous_line = first_seen_line.get(normalized)

        if normalized not in first_seen_line:
            first_seen_line[normalized] = line

        if existing or previous_line is not None:
            conflicts.append(
                {
                    "line": line,
                    "email": normalized,
                    "existing": existing,
                    "previous_line": previous_line,
                }
            )

    return conflicts
