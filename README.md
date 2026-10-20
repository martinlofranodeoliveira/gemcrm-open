# GemCRM Open

A small, self-hosted CRM in Portuguese for contacts, companies, sales opportunities
and follow-up tasks. New code, independent of any private GemCRM application.

**MIT licensed.** Anyone can download, modify and redistribute it. This is an
early version for local use and evaluation; review deployment security before
putting it on the internet.

![GemCRM Open dashboard with fictional demonstration records](docs/screenshots/dashboard.png)

The screenshot uses fictional records from `seed_demo`, not customer data.

## What works

- Account creation, login and logout.
- Companies and contacts, with search and CSV export.
- Contact CSV upload, preview and explicit, all-or-nothing confirmation.
- A five-stage sales pipeline and opportunity values.
- Follow-up tasks with open, overdue, today, upcoming and completed filters, plus a dashboard with open opportunities and due actions.
- Per-account record isolation, CSRF protection and spreadsheet-safe CSV cells.
- Responsive, keyboard-accessible server-rendered pages; no external frontend CDN.

## Filter tasks by date

Open **Tarefas** and choose the deadline filter, or request it directly:

```text
/tasks/?status=today
/tasks/?status=upcoming
/tasks/?status=today&q=retorno
```

- `status=today` lists only open tasks of your account with `due_date` equal to Django's `timezone.localdate()`.
- `status=upcoming` lists only open tasks of your account with `due_date` strictly after `timezone.localdate()`.
- `q` search combines with every status filter. Existing `open`, `overdue` and `completed` filters keep working; an unknown status falls back to `all`.
- Dates use the configured Django `TIME_ZONE`, not the browser clock. Filters only read records and never change them.

## Run locally

Requires Python 3.12 or newer and [uv](https://docs.astral.sh/uv/).

```sh
git clone https://github.com/martinlofranodeoliveira/gemcrm-open.git
cd gemcrm-open
uv sync
uv run python manage.py migrate
uv run python manage.py runserver 127.0.0.1:8093
```

Open `http://127.0.0.1:8093/accounts/signup/` and create your own account. There
are no default credentials. SQLite data and a generated development secret stay
in the ignored `.data/` directory. Never upload this directory.

Without uv, create and activate a Python virtual environment, install
`requirements.txt`, then use `python manage.py ...` for the same commands.

To populate an **empty test account** with fictional examples:

```sh
uv run python manage.py seed_demo --username YOUR_TEST_USERNAME
```

## Checks

```sh
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run python manage.py test
```

Tests cover authentication, record ownership, foreign-key isolation, CSRF,
stage changes, CSV injection, escaping, import validation, replay protection,
transaction rollback and related-record preservation.

## Import contacts from CSV

Open **Contatos → Importar CSV**, select a UTF-8 file and review the preview.
Uploading never creates contacts. Correct every listed error or duplicate, then
choose **Importar contatos** to save the complete batch. Sending another file
replaces the previous preview, even when the replacement is invalid.

```csv
name,email,phone,company,notes
Example contact,example@example.com,,,Fictional example
```

- `name` is required; `email`, `phone`, `company` and `notes` are optional.
  A UTF-8 BOM is accepted. Use commas as separators and quote values containing
  commas. Each accepted file is limited to 256 KiB and 500 contacts.
- Companies must already exist under one unambiguous, exact name in your account.
  The importer never creates companies or looks up another account's records.
- Emails repeated in the file or your existing contacts block the entire batch.
  Matching uses the policy described below. Blank emails are allowed. This does
  not merge or update records, or impose global email uniqueness on manual edits.
- Confirmation is valid for 15 minutes and rechecks current database records.
  The batch and a durable replay receipt are saved in one transaction. A second
  confirmation cannot import the same preview, including after an overlapping
  login response restores an old session. A separate canonical preview state
  also rejects old previews after another upload, including invalid replacements.
  If an overlapping session save loses the latest CSV, the importer fails closed
  and asks you to upload it again. A failed transaction saves no contacts
  or receipt, allowing a retry while the preview remains valid. SQLite write
  contention can require a retry; imports serialize per account on databases
  supporting row locks.
- The current checks support up to 20,000 existing contacts and matching company
  records per account. Larger or inconsistent data sets fail closed for review.

The workflow requires Django's database session backend. The uploaded CSV stays
in the server-side session, never a signed-cookie session or hidden form field.
The 15-minute confirmation window is **not** an automatic data deletion timer:
drafts follow the session's retention unless replaced, consumed or logged out.
Treat session storage and database backups as private contact data.

After updating an existing installation, apply migrations before serving traffic:

```sh
uv run python manage.py migrate
```

For maintenance, remove expired sessions and replay receipts with:

```sh
uv run python manage.py clearsessions
uv run python manage.py purge_contact_import_receipts
```

The cleanup removes only expired receipts and preview states; it does not touch
contacts or active previews. These records contain hashed nonce/session
identifiers, timestamps, state and the owner, not uploaded CSV. Configure an
appropriate maintenance schedule for your install.
The accepted file limit does not replace a reverse-proxy HTTP request-body limit.
See the [workflow design notes](docs/design/contact-import.md) for interface states,
accessibility behavior and validation scope.

## Preview imported contacts in Python

Two pure helpers support callers building an import workflow. `parse_contacts`
validates CSV text without writing records. `detect_duplicate_emails` flags
emails already supplied by the caller or repeated in the accepted preview:

```python
from crm.contact_import import parse_contacts
from crm.contact_duplicates import detect_duplicate_emails

preview = parse_contacts("name,email\nExample,example@example.com\n")
if preview["valid"]:
    # Supply only email addresses belonging to the current account.
    existing_emails = ["example@example.com"]  # fictional example
    duplicates = detect_duplicate_emails(preview["rows"], existing_emails)
    print(duplicates)
    # [{"line": 2, "email": "example@example.com",
    #   "existing": True, "previous_line": None}]
```

Duplicate matching trims surrounding whitespace and applies `casefold()` to
emails. Blank emails are ignored; dots, plus suffixes and provider-specific
aliases are preserved. This is an explicit CRM matching policy, not a test of
mail delivery or proof that two addresses belong to one person. Each conflict
contains exactly `line`, normalized `email`, `existing`, and `previous_line`;
the last field references the first earlier matching import row, when present.
Results retain input order and do not modify either input.

The helper accepts lists, validates addresses and unique integer row lines
starting at 2, and raises `ValueError` for malformed inputs. Defaults are
`max_rows=500` and `max_existing=20000`, independently inclusive; larger lists
are rejected, including blank or repeated entries. Both limits must be positive
integers, excluding booleans.

These helpers query no database and do not verify ownership: the caller must
filter existing emails to the current account. They neither create, merge nor
update contacts themselves. The import screen composes them with owner-scoped
lookups and transactional checks when saving.

## Deployment and data

The development server is not a production server. Production requires a WSGI
server, HTTPS reverse proxy, static-file serving, backups, `DJANGO_DEBUG=false`,
a private `DJANGO_SECRET_KEY` and explicit `DJANGO_ALLOWED_HOSTS`. Configure
secure session/CSRF cookies for HTTPS. `.env.example` documents the environment
variables; it is not automatically loaded. Run `manage.py check --deploy` against
your deployment configuration and review its findings.

Each account sees its own records. Team sharing, password-reset email, audit
logs and integrations are future work, not current capabilities.

## Contribute

See [ROADMAP.md](ROADMAP.md), [CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md).
AI-assisted work must meet the same tests and privacy requirements. One complete,
useful change belongs in one commit; no empty or artificial activity.
