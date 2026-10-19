"""Owner-scoped, server-side previews and all-or-nothing contact imports.

Imports serialize on the account row on databases with row locks. SQLite uses
its write transaction; a competing writer may need to retry. This does not add
a global email uniqueness constraint to the existing manual contact editor.
"""

import hashlib
import math
import secrets
import time
from datetime import UTC, datetime, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.db import transaction
from django.utils import timezone

from .contact_duplicates import detect_duplicate_emails
from .contact_import import parse_contacts
from .forms import CONTACT_IMPORT_MAX_BYTES, ContactForm
from .models import Company, Contact, ContactImportReceipt, ContactImportState


MAX_ROWS = 500
MAX_EXISTING = 20000
PREVIEW_SECONDS = 15 * 60
DRAFT_SESSION_KEY = "contact_import_preview"

_PARSE_MESSAGES = {
    "Header is required": "Inclua o cabeçalho do CSV.",
    "Header must include name": "O cabeçalho deve incluir a coluna name.",
    "Unknown header column": "O cabeçalho contém uma coluna desconhecida.",
    "Duplicate header column": "O cabeçalho contém uma coluna repetida.",
    "Row limit exceeded": "O arquivo deve ter no máximo 500 contatos.",
    "Row width mismatch": "A quantidade de campos difere do cabeçalho.",
    "Name is required": "O nome é obrigatório.",
    "Invalid email": "O e-mail é inválido.",
    "Malformed CSV": "O CSV está malformado; revise aspas e separadores.",
}
_FIELD_LABELS = {
    "name": "nome", "email": "e-mail", "phone": "telefone",
    "company": "empresa", "notes": "observações",
}


class PreviewUnavailable(Exception):
    """A preview is missing, expired, consumed, or belongs to another session."""


class ImportRejected(Exception):
    def __init__(self, preview):
        self.preview = preview
        super().__init__("The import no longer passes validation.")


def database_sessions_enabled():
    # A signed-cookie session would put the uploaded CSV in the browser.
    return settings.SESSION_ENGINE == "django.contrib.sessions.backends.db"


def _prepare_contacts(owner, text):
    result = parse_contacts(text, max_rows=MAX_ROWS)
    preview = {
        "rows": result["rows"],
        "errors": [
            {"line": error["line"], "message": _PARSE_MESSAGES[error["message"]]}
            for error in result["errors"]
        ],
        "duplicates": [],
        "duplicate_lines": [],
        "valid": False,
    }
    if not result["rows"] and result["valid"]:
        preview["errors"].append({"line": 1, "message": "Inclua ao menos um contato."})

    company_names = {row["company"] for row in result["rows"] if row["company"]}
    company_matches = {}
    for company in Company.objects.filter(owner=owner, name__in=company_names)[:MAX_EXISTING + 1]:
        company_matches.setdefault(company.name, []).append(company)
    if sum(map(len, company_matches.values())) > MAX_EXISTING:
        preview["errors"].append({"line": 1, "message": "Há muitas empresas correspondentes; revise o cadastro antes de importar."})

    contacts = []
    for row in result["rows"]:
        company = None
        if row["company"]:
            matches = company_matches.get(row["company"], [])
            if len(matches) != 1:
                preview["errors"].append({
                    "line": row["line"],
                    "message": "A empresa deve corresponder a um único nome exato da sua conta.",
                })
                continue
            company = matches[0]
        data = {field: row[field] for field in ("name", "email", "phone", "notes")}
        data["company"] = company.pk if company else ""
        form = ContactForm(data, owner=owner)
        if not form.is_valid():
            for field in form.errors:
                preview["errors"].append({
                    "line": row["line"],
                    "message": f"Valor inválido em {_FIELD_LABELS.get(field, 'contato')}.",
                })
        else:
            contacts.append(form.save(commit=False))

    existing = list(Contact.objects.filter(owner=owner).values_list("email", flat=True)[:MAX_EXISTING + 1])
    try:
        preview["duplicates"] = detect_duplicate_emails(
            result["rows"], existing, max_rows=MAX_ROWS, max_existing=MAX_EXISTING,
        )
    except ValueError:
        preview["errors"].append({
            "line": 1,
            "message": "Não foi possível verificar os e-mails existentes. Revise o cadastro ou o limite de 20.000 contatos.",
        })
    preview["duplicate_lines"] = [item["line"] for item in preview["duplicates"]]
    preview["valid"] = not preview["errors"] and not preview["duplicates"]
    return preview, contacts


def preview_contacts(owner, text):
    return _prepare_contacts(owner, text)[0]


def _session_digest(session):
    if not database_sessions_enabled():
        raise PreviewUnavailable
    if not session.session_key:
        session.create()
    return hashlib.sha256(session.session_key.encode("utf-8")).hexdigest()


def _nonce_digest(token):
    if not isinstance(token, str) or not 1 <= len(token) <= 100 or not token.isascii():
        raise PreviewUnavailable
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def begin_preview(session, owner):
    """Durably invalidate any preceding preview before validating this upload."""
    token = secrets.token_urlsafe(32)
    session_digest = _session_digest(session)
    issued_at = datetime.fromtimestamp(time.time(), tz=UTC)
    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=owner.pk)
        ContactImportState.objects.update_or_create(
            owner=owner, session_digest=session_digest,
            defaults={
                "nonce_digest": _nonce_digest(token),
                "ready": False,
                "issued_at": issued_at,
                "expires_at": issued_at + timedelta(seconds=PREVIEW_SECONDS),
            },
        )
    return token


def _current_state(session, owner, token, *, ready):
    state = ContactImportState.objects.select_for_update().filter(
        owner=owner, session_digest=_session_digest(session),
        nonce_digest=_nonce_digest(token), ready=ready,
    ).first()
    if state is None or not 0 <= time.time() - state.issued_at.timestamp() < PREVIEW_SECONDS:
        raise PreviewUnavailable
    if state.expires_at != state.issued_at + timedelta(seconds=PREVIEW_SECONDS):
        raise PreviewUnavailable
    return state


def save_preview(session, owner, text, *, attempt_token=None):
    token = attempt_token if attempt_token is not None else begin_preview(session, owner)
    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=owner.pk)
        state = _current_state(session, owner, token, ready=False)
        state.ready = True
        state.save(update_fields=["ready"])
    session[DRAFT_SESSION_KEY] = {
        "token": token,
        "owner_id": owner.pk,
        "created_at": state.issued_at.timestamp(),
        "csv_text": text,
    }
    return token


def _validated_draft(data, owner, token):
    draft = data.get(DRAFT_SESSION_KEY)
    if (
        not isinstance(draft, dict)
        or not isinstance(token, str)
        or not 1 <= len(token) <= 100
        or not token.isascii()
    ):
        raise PreviewUnavailable
    expected = draft.get("token")
    created = draft.get("created_at")
    text = draft.get("csv_text")
    now = time.time()
    if (
        not isinstance(expected, str)
        or not expected.isascii()
        or not secrets.compare_digest(expected, token)
        or draft.get("owner_id") != owner.pk
        or isinstance(created, bool)
        or not isinstance(created, (int, float))
        or not math.isfinite(created)
        or not 0 <= now - created < PREVIEW_SECONDS
        or not isinstance(text, str)
    ):
        raise PreviewUnavailable
    try:
        size = len(text.encode("utf-8", errors="strict"))
    except UnicodeEncodeError:
        raise PreviewUnavailable from None
    if size > CONTACT_IMPORT_MAX_BYTES:
        raise PreviewUnavailable
    return text


def confirm_contacts(session, owner, token):
    """Record a durable receipt and save all rows in the same transaction.

    A unique nonce digest prevents replay even if a concurrent login response
    restores an older session blob containing the draft. Validation and write
    failures roll everything back, including the receipt and session changes.
    No client-supplied row data is consulted.
    """
    if not database_sessions_enabled() or not session.session_key:
        raise PreviewUnavailable
    with transaction.atomic():
        # Serialize imports from different sessions belonging to one account
        # on databases supporting row locks. This does not mutate the account.
        get_user_model().objects.select_for_update().get(pk=owner.pk)
        try:
            stored_session = Session.objects.select_for_update().get(
                session_key=session.session_key, expire_date__gt=timezone.now(),
            )
        except Session.DoesNotExist:
            raise PreviewUnavailable from None
        data = stored_session.get_decoded()
        text = _validated_draft(data, owner, token)
        state = _current_state(session, owner, token, ready=True)
        nonce_digest = _nonce_digest(token)
        if ContactImportReceipt.objects.filter(nonce_digest=nonce_digest).exists():
            raise PreviewUnavailable
        del data[DRAFT_SESSION_KEY]
        consumed = Session.objects.filter(
            session_key=stored_session.session_key,
            session_data=stored_session.session_data,
        ).update(session_data=session.encode(data))
        if consumed != 1:
            raise PreviewUnavailable
        # The unique database constraint, rather than the session blob, is the
        # final authority if two requests race to confirm the same preview.
        ContactImportReceipt.objects.create(
            nonce_digest=nonce_digest,
            owner=owner,
            session_digest=_session_digest(session),
            expires_at=state.expires_at,
        )
        state.ready = False
        state.save(update_fields=["ready"])
        preview, contacts = _prepare_contacts(owner, text)
        if not preview["valid"]:
            raise ImportRejected(preview)
        # Company ownership is checked again by ContactForm above. Model
        # validation remains enabled instead of bypassing it with bulk_create.
        for contact in contacts:
            contact.save()

    # Prevent SessionMiddleware from saving the stale, consumed preview again.
    # Keep the current persisted authentication/session values unchanged.
    session.clear()
    session.update(data)
    session.modified = False
    return len(contacts)
