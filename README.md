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

## Paginate contacts

Open **Contatos** to browse only your account's contacts ordered by name then pk.

```text
/contacts/?q=marina
/contacts/?q=marina&page=2
/contacts/export/?q=marina
```

- Lists exactly 50 contacts per page. `q` filters by name, e-mail, phone or company after `q.strip()[:200]`.
- `page` uses Django `Paginator.get_page(request.GET.get("page"))`: missing, empty or non-integer shows the first page; zero, negative or beyond the last shows the last page. An empty result is page 1 of 1 with 0 records.
- Multi-page results show `Página X de Y` in `nav[aria-label="Paginação de contatos"]` with `rel="prev"`/`rel="next"` links only when available. Page URLs keep only `page` and the normalized `q` when non-empty.
- CSV export ignores `page` and exports all filtered contacts of your account.

## Relatório de pipeline por previsão

HTML em `/reports/pipeline/` e CSV em `/reports/pipeline/export/`.

- Query fechada com `start` e `end` em `AAAA-MM-DD`; ausência ou vazio sem filtro.
- Sem filtros inclui `expected_close` nulo; com qualquer data só conta previsão dentro do intervalo inclusivo.
- Mostra etapa e valor atuais por previsão; não é histórico, receita realizada, conversão ou garantia futura.
- HTML usa `R$ 1234,50` e CSV usa `1234.50`, ambos com duas casas e sem separador de milhar.
- Filtros inválidos retornam 400 sem tabela nem CSV.

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


<!-- community-core:pipeline-forecast-filter -->
### Pipeline forecast filter and totals core

Lets the Portuguese self-hosted CRM build the documented pipeline-by-forecast report from pure JSON without database or clock reads. It mirrors /reports/pipeline/ filtering: empty start/end keeps null forecasts, any bound keeps only inclusive in-range dates, invalid bounds are rejected for 400 handling, and per-stage plus grand totals are formatted as R$ 1234,50 for HTML and 1234.50 for CSV with no thousand separator. Ownership filtering stays with the caller.

Reusable deterministic JSON core: `crm/features/pipeline_forecast_filter.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) -> dict as a pure deterministic function with no I/O, env, time, randomness, callbacks or dependencies. Input payload must be an object with optional keys: deals (list, default []), start (str or None, default None), end (str or None, default None). Each deal must be an object with pk int (booleans rejected), title str, stage str one of new, qualified, proposal, won, lost, value str matching ^(0|[1-9][0-9]*)(\.[0-9]{1,2})?$ with total cents <=99999999999999, expected_close str or None; extra keys ignored. Missing/None/empty-string start/end means unbounded; otherwise must be YYYY-MM-DD valid calendar date else ValueError. If both bounded and start>end raise ValueError. Deals longer than 5000 raise ValueError. Titles must be str else ValueError. Expected_close None/missing/"" means null; otherwise must be YYYY-MM-DD valid calendar date else ValueError. Steps: 1) Normalize start/end to None when missing/None/"" else validated string. 2) Convert each value to integer cents ("100"->10000, "100.5"->10050, "100.05"->10005) without float. 3) Filter in input order: when both bounds None keep all including null; otherwise keep only non-null dates with (start is None or d>=start) and (end is None or d<=end) lexicographically equal to chronological for YYYY-MM-DD. 4) Build results list copying pk,title,stage, expected_close (None for null), value_cents int, value_csv "1234.50" exactly two decimals no thousand separator, value_display "R$ 1234,50" exactly two decimals comma decimal no thousand separator. 5) Aggregate by_stage in fixed order new,qualified,proposal,won,lost each as {count int, total_cents int, total_csv str, total_display str} with zero as "0.00"/"R$ 0,00", plus grand {count,total_cents,total_csv,total_display}. Returns dict with start, end (normalized None or string), total_count int, results list, by_stage object, grand object. Raises ValueError on malformed types or dates. Caller must pre-filter deals to current account and map ValueError to 400 with no table/CSV; function does no ownership check, DB query, CSV file handling, or clock read and never mutates inputs. Totals reflect current stage/value snapshot, not history, realized revenue, conversion, or future guarantee.

Examples (JSON input and expected output):

```json
{
  "input": {
    "deals": [
      {
        "expected_close": null,
        "pk": 1,
        "stage": "new",
        "title": "Padaria",
        "value": "100.00"
      },
      {
        "expected_close": "2026-03-10",
        "pk": 2,
        "stage": "won",
        "title": "Mercado",
        "value": "234.50"
      }
    ]
  },
  "output": {
    "by_stage": {
      "lost": {
        "count": 0,
        "total_cents": 0,
        "total_csv": "0.00",
        "total_display": "R$ 0,00"
      },
      "new": {
        "count": 1,
        "total_cents": 10000,
        "total_csv": "100.00",
        "total_display": "R$ 100,00"
      },
      "proposal": {
        "count": 0,
        "total_cents": 0,
        "total_csv": "0.00",
        "total_display": "R$ 0,00"
      },
      "qualified": {
        "count": 0,
        "total_cents": 0,
        "total_csv": "0.00",
        "total_display": "R$ 0,00"
      },
      "won": {
        "count": 1,
        "total_cents": 23450,
        "total_csv": "234.50",
        "total_display": "R$ 234,50"
      }
    },
    "end": null,
    "grand": {
      "count": 2,
      "total_cents": 33450,
      "total_csv": "334.50",
      "total_display": "R$ 334,50"
    },
    "results": [
      {
        "expected_close": null,
        "pk": 1,
        "stage": "new",
        "title": "Padaria",
        "value_cents": 10000,
        "value_csv": "100.00",
        "value_display": "R$ 100,00"
      },
      {
        "expected_close": "2026-03-10",
        "pk": 2,
        "stage": "won",
        "title": "Mercado",
        "value_cents": 23450,
        "value_csv": "234.50",
        "value_display": "R$ 234,50"
      }
    ],
    "start": null,
    "total_count": 2
  }
}
```

```json
{
  "input": {
    "deals": [
      {
        "expected_close": null,
        "pk": 1,
        "stage": "new",
        "title": "Padaria",
        "value": "100.00"
      },
      {
        "expected_close": "2026-03-10",
        "pk": 2,
        "stage": "won",
        "title": "Mercado",
        "value": "234.50"
      }
    ],
    "end": "2026-03-31",
    "start": "2026-03-01"
  },
  "output": {
    "by_stage": {
      "lost": {
        "count": 0,
        "total_cents": 0,
        "total_csv": "0.00",
        "total_display": "R$ 0,00"
      },
      "new": {
        "count": 0,
        "total_cents": 0,
        "total_csv": "0.00",
        "total_display": "R$ 0,00"
      },
      "proposal": {
        "count": 0,
        "total_cents": 0,
        "total_csv": "0.00",
        "total_display": "R$ 0,00"
      },
      "qualified": {
        "count": 0,
        "total_cents": 0,
        "total_csv": "0.00",
        "total_display": "R$ 0,00"
      },
      "won": {
        "count": 1,
        "total_cents": 23450,
        "total_csv": "234.50",
        "total_display": "R$ 234,50"
      }
    },
    "end": "2026-03-31",
    "grand": {
      "count": 1,
      "total_cents": 23450,
      "total_csv": "234.50",
      "total_display": "R$ 234,50"
    },
    "results": [
      {
        "expected_close": "2026-03-10",
        "pk": 2,
        "stage": "won",
        "title": "Mercado",
        "value_cents": 23450,
        "value_csv": "234.50",
        "value_display": "R$ 234,50"
      }
    ],
    "start": "2026-03-01",
    "total_count": 1
  }
}
```

```json
{
  "input": {
    "deals": [
      {
        "expected_close": "2026-03-01",
        "pk": 3,
        "stage": "proposal",
        "title": "Oficina",
        "value": "100.5"
      },
      {
        "expected_close": "2026-02-28",
        "pk": 4,
        "stage": "proposal",
        "title": "Cafe",
        "value": "20.05"
      }
    ],
    "end": null,
    "start": "2026-03-01"
  },
  "output": {
    "by_stage": {
      "lost": {
        "count": 0,
        "total_cents": 0,
        "total_csv": "0.00",
        "total_display": "R$ 0,00"
      },
      "new": {
        "count": 0,
        "total_cents": 0,
        "total_csv": "0.00",
        "total_display": "R$ 0,00"
      },
      "proposal": {
        "count": 1,
        "total_cents": 10050,
        "total_csv": "100.50",
        "total_display": "R$ 100,50"
      },
      "qualified": {
        "count": 0,
        "total_cents": 0,
        "total_csv": "0.00",
        "total_display": "R$ 0,00"
      },
      "won": {
        "count": 0,
        "total_cents": 0,
        "total_csv": "0.00",
        "total_display": "R$ 0,00"
      }
    },
    "end": null,
    "grand": {
      "count": 1,
      "total_cents": 10050,
      "total_csv": "100.50",
      "total_display": "R$ 100,50"
    },
    "results": [
      {
        "expected_close": "2026-03-01",
        "pk": 3,
        "stage": "proposal",
        "title": "Oficina",
        "value_cents": 10050,
        "value_csv": "100.50",
        "value_display": "R$ 100,50"
      }
    ],
    "start": "2026-03-01",
    "total_count": 1
  }
}
```

Public regression tests: `crm/test_community_pipeline_forecast_filter.py`.
