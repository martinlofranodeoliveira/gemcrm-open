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


<!-- community-core:csv-cell-guard -->
### Spreadsheet-safe CSV cell guard core

Lets the Portuguese self-hosted CRM export contacts, companies and pipeline rows as spreadsheet-safe cells from pure JSON without database reads. It prefixes formula-trigger text with a single quote while leaving safe text unchanged, preserving export content. Ownership filtering and CSV quoting stay with the caller.

Reusable deterministic JSON core: `crm/features/csv_cell_guard.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) -> dict as a pure deterministic function with no I/O, env, time, randomness, callbacks or dependencies. Input payload must be an object with optional key cells (list, default []). Each cell must be str with length <=5000; extra keys ignored. Reject with ValueError if payload is not an object, cells is not a list, len(cells)>2000, or any cell is not str or exceeds length. Uses only plain functions and immutable literal module constants with local mutable containers. Steps: 1) Preserve inputs without mutation. 2) For each cell in input order with index from 0 compute stripped by removing leading SP, TAB, CR, LF only, then flagged is True when stripped is non-empty and its first character is one of =, +, -, @, |, % else False. 3) Compute safe as original cell when not flagged else single-quote plus original cell preserving all leading whitespace. 4) Build results list each as {index int, source str copy, safe str, flagged bool} in input order. 5) Count flagged_count. Returns dict with total_count int equal to len(cells), flagged_count int, results list. Raises ValueError on malformed types or limit violations. Caller must stringify non-string values before calling and apply ownership filtering and CSV quoting separately; function does no ownership check, DB query, CSV file handling, or clock read and never mutates inputs. Guard is a snapshot formula-prefix mitigation, not a guarantee against all spreadsheet behaviors.

Examples (JSON input and expected output):

```json
{
  "input": {
    "cells": [
      "hello",
      "=SUM(A1)",
      " @test"
    ]
  },
  "output": {
    "flagged_count": 2,
    "results": [
      {
        "flagged": false,
        "index": 0,
        "safe": "hello",
        "source": "hello"
      },
      {
        "flagged": true,
        "index": 1,
        "safe": "'=SUM(A1)",
        "source": "=SUM(A1)"
      },
      {
        "flagged": true,
        "index": 2,
        "safe": "' @test",
        "source": " @test"
      }
    ],
    "total_count": 3
  }
}
```

```json
{
  "input": {
    "cells": [
      "-5",
      "  +calc",
      "normal, value"
    ]
  },
  "output": {
    "flagged_count": 2,
    "results": [
      {
        "flagged": true,
        "index": 0,
        "safe": "'-5",
        "source": "-5"
      },
      {
        "flagged": true,
        "index": 1,
        "safe": "'  +calc",
        "source": "  +calc"
      },
      {
        "flagged": false,
        "index": 2,
        "safe": "normal, value",
        "source": "normal, value"
      }
    ],
    "total_count": 3
  }
}
```

Public regression tests: `crm/test_community_csv_cell_guard.py`.


<!-- community-core:company-name-resolver -->
### Import company name resolver core

Lets the Portuguese self-hosted CRM resolve contact-import company names against one account's exact company list from pure JSON without database reads. It mirrors the documented import rule where companies must already exist under one unambiguous exact name, blank means no link, and missing or ambiguous names block the batch. Ownership filtering and contact creation stay with the caller.

Reusable deterministic JSON core: `crm/features/company_name_resolver.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) -> dict as a pure deterministic function with no I/O, env, time, randomness, callbacks or dependencies. Input payload must be an object with optional keys: companies (list, default []), rows (list, default []). Each company must be an object with pk int >=1 (booleans rejected) and name str length 1..180; extra keys ignored. Each row must be an object with line int >=2 (booleans rejected, unique across rows) and company str length 0..180; extra keys ignored. Reject with ValueError if payload is not an object, companies/rows are not lists, len(companies)>2000, len(rows)>500, any entry malformed, any string exceeds limit, or any line duplicates. Uses only plain functions and immutable literal module constants with local mutable containers. Steps: 1) Preserve inputs without mutation. 2) Index companies by exact name (case-sensitive, no trim/casefold) mapping name to first pk and ambiguous flag when same name appears for different pks. 3) For each row in input order with company == "" treat as empty with status "empty" and company_pk None; otherwise exact lookup: single pk gives status "resolved" with that pk, no entry gives status "missing" with None, multiple pks give status "ambiguous" with None. 4) Build results list in input order each as {line int, company str copy, status str, company_pk int or None}. 5) Count resolved_count, empty_count, missing_count, ambiguous_count and can_import True only when missing_count==0 and ambiguous_count==0. Returns dict with total_count int equal to len(rows), resolved_count, empty_count, missing_count, ambiguous_count, can_import bool, results list. Raises ValueError on malformed types or limit violations. Caller must pre-filter companies to current account and supply only that account's exact names; function does no ownership check, DB query, CSV file handling, or clock read and never mutates inputs. Exact match is a snapshot import guard, not company creation, merging, or delivery proof.

Examples (JSON input and expected output):

```json
{
  "input": {
    "companies": [
      {
        "name": "Padaria Sol",
        "pk": 1
      }
    ],
    "rows": [
      {
        "company": "Padaria Sol",
        "line": 2
      },
      {
        "company": "",
        "line": 3
      }
    ]
  },
  "output": {
    "ambiguous_count": 0,
    "can_import": true,
    "empty_count": 1,
    "missing_count": 0,
    "resolved_count": 1,
    "results": [
      {
        "company": "Padaria Sol",
        "company_pk": 1,
        "line": 2,
        "status": "resolved"
      },
      {
        "company": "",
        "company_pk": null,
        "line": 3,
        "status": "empty"
      }
    ],
    "total_count": 2
  }
}
```

```json
{
  "input": {
    "companies": [
      {
        "name": "Mercado",
        "pk": 1
      },
      {
        "name": "Mercado",
        "pk": 2
      }
    ],
    "rows": [
      {
        "company": "Mercado",
        "line": 2
      }
    ]
  },
  "output": {
    "ambiguous_count": 1,
    "can_import": false,
    "empty_count": 0,
    "missing_count": 0,
    "resolved_count": 0,
    "results": [
      {
        "company": "Mercado",
        "company_pk": null,
        "line": 2,
        "status": "ambiguous"
      }
    ],
    "total_count": 1
  }
}
```

```json
{
  "input": {
    "companies": [
      {
        "name": "Acme",
        "pk": 5
      }
    ],
    "rows": [
      {
        "company": "acme",
        "line": 2
      },
      {
        "company": "Desconhecida",
        "line": 3
      }
    ]
  },
  "output": {
    "ambiguous_count": 0,
    "can_import": false,
    "empty_count": 0,
    "missing_count": 2,
    "resolved_count": 0,
    "results": [
      {
        "company": "acme",
        "company_pk": null,
        "line": 2,
        "status": "missing"
      },
      {
        "company": "Desconhecida",
        "company_pk": null,
        "line": 3,
        "status": "missing"
      }
    ],
    "total_count": 2
  }
}
```

Public regression tests: `crm/test_community_company_name_resolver.py`.


<!-- community-core:task-date-filter -->
### Task date status filter core

Lets the Portuguese self-hosted CRM list follow-up tasks by documented date status from pure JSON without database or clock reads. It mirrors Tarefas open, overdue, today, upcoming, completed and all filters with combined title search, explicit today reference, due-date ordering and read-only snapshot semantics. Ownership filtering stays with the caller.

Reusable deterministic JSON core: `crm/features/task_date_filter.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) -> dict as a pure deterministic function with no I/O, env, time, randomness, callbacks or dependencies. Input payload must be an object with optional keys: tasks (list, default empty), today (str), status (str or None, default None), q (str or None, default None); extra keys ignored. Each task must be an object with pk int from 1 to 9007199254740991 (booleans rejected), title str length 1 to 180, due_date str YYYY-MM-DD valid calendar date, completed bool strictly; extra keys ignored. Reject with ValueError if payload is not an object, tasks is not a list, len tasks over 5000, any task malformed, today missing or not valid YYYY-MM-DD calendar date, status is not str or None, or q is not str or None. Normalize status_effective to all when missing or None, else when str keep exact match one of all, open, overdue, today, upcoming, completed otherwise fallback to all including empty and unknown. Normalize q to empty when missing or None else q stripped and first 200 characters. Validate today and every due_date as YYYY-MM-DD with month 01 to 12 and day valid for month including leap-year February 29, else ValueError. Uses only plain functions and immutable literal module constants with local mutable containers. Steps: 1 Preserve inputs without mutation. 2 Filter by status_effective: all keeps all; open keeps completed false; completed keeps completed true; overdue keeps completed false and due_date before today; today keeps completed false and due_date equal to today; upcoming keeps completed false and due_date after today using lexicographic comparison equal to chronological for YYYY-MM-DD. 3 When normalized q is non-empty keep only tasks where q casefold is substring of title casefold. 4 Sort kept tasks by completed false before true, then due_date ascending, then pk ascending. 5 Build results list copying only pk, title, due_date, completed in sorted order. Returns dict with today str, status_effective str, q normalized str, total_count int equal to len tasks, filtered_count int equal to len results, results list. Raises ValueError on malformed types, dates or limit violations. Caller must pre-filter tasks to current account and supply configured TIME_ZONE localdate as today; function does no ownership check, DB query, CSV handling, or clock read and never mutates inputs. Snapshot filtering only reads records and never changes them.

Examples (JSON input and expected output):

```json
{
  "input": {
    "q": "",
    "status": "today",
    "tasks": [
      {
        "completed": false,
        "due_date": "2026-03-09",
        "pk": 1,
        "title": "Retorno Marina"
      },
      {
        "completed": false,
        "due_date": "2026-03-10",
        "pk": 2,
        "title": "Retorno Joao"
      },
      {
        "completed": false,
        "due_date": "2026-03-11",
        "pk": 3,
        "title": "Proposta final"
      },
      {
        "completed": true,
        "due_date": "2026-03-10",
        "pk": 4,
        "title": "Fechado"
      }
    ],
    "today": "2026-03-10"
  },
  "output": {
    "filtered_count": 1,
    "q": "",
    "results": [
      {
        "completed": false,
        "due_date": "2026-03-10",
        "pk": 2,
        "title": "Retorno Joao"
      }
    ],
    "status_effective": "today",
    "today": "2026-03-10",
    "total_count": 4
  }
}
```

```json
{
  "input": {
    "q": "  retorno ",
    "status": "weird",
    "tasks": [
      {
        "completed": false,
        "due_date": "2026-03-09",
        "pk": 5,
        "title": "Retorno Marina"
      },
      {
        "completed": false,
        "due_date": "2026-03-09",
        "pk": 6,
        "title": "Ligar fornecedor"
      },
      {
        "completed": false,
        "due_date": "2026-03-12",
        "pk": 7,
        "title": "RETORNO urgente"
      }
    ],
    "today": "2026-03-10"
  },
  "output": {
    "filtered_count": 2,
    "q": "retorno",
    "results": [
      {
        "completed": false,
        "due_date": "2026-03-09",
        "pk": 5,
        "title": "Retorno Marina"
      },
      {
        "completed": false,
        "due_date": "2026-03-12",
        "pk": 7,
        "title": "RETORNO urgente"
      }
    ],
    "status_effective": "all",
    "today": "2026-03-10",
    "total_count": 3
  }
}
```

```json
{
  "input": {
    "q": "",
    "status": "overdue",
    "tasks": [
      {
        "completed": false,
        "due_date": "2026-01-01",
        "pk": 1,
        "title": "Atrasada aberta"
      },
      {
        "completed": true,
        "due_date": "2026-01-01",
        "pk": 2,
        "title": "Atrasada fechada"
      },
      {
        "completed": false,
        "due_date": "2026-03-10",
        "pk": 3,
        "title": "Hoje aberta"
      }
    ],
    "today": "2026-03-10"
  },
  "output": {
    "filtered_count": 1,
    "q": "",
    "results": [
      {
        "completed": false,
        "due_date": "2026-01-01",
        "pk": 1,
        "title": "Atrasada aberta"
      }
    ],
    "status_effective": "overdue",
    "today": "2026-03-10",
    "total_count": 3
  }
}
```

Public regression tests: `crm/test_community_task_date_filter.py`.


<!-- community-core:record-ownership-guard -->
### Record ownership isolation check core

Lets the Portuguese self-hosted CRM verify per-account record ownership and foreign-key isolation from pure JSON without database reads. It mirrors OwnedRecord.validate_related_owners for companies, contacts, deals and tasks so callers can snapshot-check that records and their links belong to one account. Ownership enforcement and record creation stay with the caller.

Reusable deterministic JSON core: `crm/features/record_ownership_guard.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) -> dict as a pure deterministic function with no I/O, env, time, randomness, callbacks or dependencies. Input payload must be an object with required key owner int >=1 and <=9007199254740991 (booleans rejected) and optional key records (list, default []); extra keys ignored. Each record must be an object with kind str one of company, contact, deal, task, pk int >=1 and <=9007199254740991 (booleans rejected), owner int >=1 and <=9007199254740991 (booleans rejected), plus optional link keys company_owner, contact_owner, deal_owner each int in range or None (booleans rejected, missing means None); extra keys ignored. Reject with ValueError if payload is not an object, owner missing or malformed, records is not a list, len(records)>5000, any record malformed, any link malformed, or per-kind link allowance violated. Uses only plain functions and immutable literal module constants with local mutable containers. Steps: 1) Preserve inputs without mutation. 2) Normalize missing links to None. Enforce allowance: company requires all links None; contact requires contact_owner and deal_owner None; deal requires deal_owner None; task requires company_owner and contact_owner None, else ValueError. 3) For each record in input order compute owned as record owner equals payload owner, isolated as every allowed link is None or equals record owner, accessible as owned and isolated. 4) Build results list in input order each as {kind, pk, owner, company_owner, contact_owner, deal_owner, owned, isolated, accessible}. 5) Count owned_count, isolated_count, accessible_count. Returns dict with owner, total_count equal to len(records), owned_count, isolated_count, accessible_count, results list. Raises ValueError on malformed types or limit violations. Caller must still scope database queries to the current account and enforce authentication; function does no ownership enforcement, DB query, CSV handling, or clock read and never mutates inputs. Snapshot check only, not creation, merging, updating, deletion, sharing, or delivery proof.

Examples (JSON input and expected output):

```json
{
  "input": {
    "owner": 7,
    "records": [
      {
        "kind": "company",
        "owner": 7,
        "pk": 1
      },
      {
        "company_owner": 7,
        "kind": "contact",
        "owner": 7,
        "pk": 2
      },
      {
        "company_owner": 9,
        "kind": "contact",
        "owner": 7,
        "pk": 3
      }
    ]
  },
  "output": {
    "accessible_count": 2,
    "isolated_count": 2,
    "owned_count": 3,
    "owner": 7,
    "results": [
      {
        "accessible": true,
        "company_owner": null,
        "contact_owner": null,
        "deal_owner": null,
        "isolated": true,
        "kind": "company",
        "owned": true,
        "owner": 7,
        "pk": 1
      },
      {
        "accessible": true,
        "company_owner": 7,
        "contact_owner": null,
        "deal_owner": null,
        "isolated": true,
        "kind": "contact",
        "owned": true,
        "owner": 7,
        "pk": 2
      },
      {
        "accessible": false,
        "company_owner": 9,
        "contact_owner": null,
        "deal_owner": null,
        "isolated": false,
        "kind": "contact",
        "owned": true,
        "owner": 7,
        "pk": 3
      }
    ],
    "total_count": 3
  }
}
```

```json
{
  "input": {
    "owner": 5,
    "records": [
      {
        "company_owner": 5,
        "contact_owner": null,
        "kind": "deal",
        "owner": 5,
        "pk": 10
      },
      {
        "deal_owner": 9,
        "kind": "task",
        "owner": 9,
        "pk": 11
      }
    ]
  },
  "output": {
    "accessible_count": 1,
    "isolated_count": 2,
    "owned_count": 1,
    "owner": 5,
    "results": [
      {
        "accessible": true,
        "company_owner": 5,
        "contact_owner": null,
        "deal_owner": null,
        "isolated": true,
        "kind": "deal",
        "owned": true,
        "owner": 5,
        "pk": 10
      },
      {
        "accessible": false,
        "company_owner": null,
        "contact_owner": null,
        "deal_owner": 9,
        "isolated": true,
        "kind": "task",
        "owned": false,
        "owner": 9,
        "pk": 11
      }
    ],
    "total_count": 2
  }
}
```

```json
{
  "input": {
    "owner": 3
  },
  "output": {
    "accessible_count": 0,
    "isolated_count": 0,
    "owned_count": 0,
    "owner": 3,
    "results": [],
    "total_count": 0
  }
}
```

Public regression tests: `crm/test_community_record_ownership_guard.py`.


<!-- community-core:contact-list-pagination -->
### Contact search and pagination snapshot core

Lets the Portuguese self-hosted CRM browse account contacts by documented name, email, phone or company search with stable name-then-pk ordering and 50-per-page navigation from pure JSON without database reads. It mirrors Contatos list, page fallback, and export-ignores-page semantics. Ownership filtering stays with the caller.

Reusable deterministic JSON core: `crm/features/contact_list_pagination.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) -> dict as a pure deterministic function with no I/O, env, time, randomness, callbacks or dependencies. Input payload must be an object with optional keys: contacts (list, default []), q (str or None, default None), page (str or int or None, default None); extra keys ignored. Each contact must be an object with pk int 1 to 9007199254740991 (booleans rejected), name str length 1 to 180, email str length 0 to 254, phone str length 0 to 40, company str length 0 to 180; extra keys ignored. Reject with ValueError if payload is not an object, contacts is not a list, len(contacts)>2000, any contact malformed, q is not str or None, page is not str or int or None (booleans rejected). Uses only plain functions and immutable literal module constants with local mutable containers. Steps: 1 Preserve inputs without mutation. 2 Normalize q to empty when missing or None else strip then first 200 characters; when normalized empty keep all contacts else keep only contacts where normalized casefold is substring of name casefold or email casefold or phone casefold or company casefold. 3 Sort kept contacts by name Unicode codepoint then pk ascending. 4 Paginate with per_page 50: total_count equals kept length, total_pages equals ceil(total_count/50) or 1 when zero. Parse page to page_effective: missing or None gives 1; int gives that value; str stripped empty gives 1; str matching optional sign plus digits parses as int else gives 1; other types already rejected. When parsed value between 1 and total_pages inclusive use it, otherwise use total_pages for zero negative and beyond-last, where invalid non-integer already mapped to 1. 5 Slice sorted list for page_effective and build results copying only pk, name, email, phone, company. Returns dict with q normalized str, page_effective int, per_page 50, total_count int, total_pages int, has_previous bool, has_next bool, prev_page int or None, next_page int or None, results list. Raises ValueError on malformed types or limit violations. Caller must pre-filter contacts to current account and keep CSV export over all filtered contacts ignoring page; function does no ownership check, DB query, CSV handling, or clock read and never mutates inputs. Read-only snapshot only.

Examples (JSON input and expected output):

```json
{
  "input": {
    "contacts": [
      {
        "company": "Padaria",
        "email": "marina@example.com",
        "name": "Marina Silva",
        "phone": "",
        "pk": 2
      },
      {
        "company": "",
        "email": "",
        "name": "Ana Souza",
        "phone": "",
        "pk": 1
      }
    ],
    "q": "marina"
  },
  "output": {
    "has_next": false,
    "has_previous": false,
    "next_page": null,
    "page_effective": 1,
    "per_page": 50,
    "prev_page": null,
    "q": "marina",
    "results": [
      {
        "company": "Padaria",
        "email": "marina@example.com",
        "name": "Marina Silva",
        "phone": "",
        "pk": 2
      }
    ],
    "total_count": 1,
    "total_pages": 1
  }
}
```

```json
{
  "input": {
    "contacts": [
      {
        "company": "Padaria",
        "email": "marina@example.com",
        "name": "Marina Silva",
        "phone": "",
        "pk": 2
      },
      {
        "company": "",
        "email": "",
        "name": "Ana Souza",
        "phone": "",
        "pk": 1
      }
    ],
    "page": "2",
    "q": ""
  },
  "output": {
    "has_next": false,
    "has_previous": false,
    "next_page": null,
    "page_effective": 1,
    "per_page": 50,
    "prev_page": null,
    "q": "",
    "results": [
      {
        "company": "",
        "email": "",
        "name": "Ana Souza",
        "phone": "",
        "pk": 1
      },
      {
        "company": "Padaria",
        "email": "marina@example.com",
        "name": "Marina Silva",
        "phone": "",
        "pk": 2
      }
    ],
    "total_count": 2,
    "total_pages": 1
  }
}
```

```json
{
  "input": {
    "contacts": [
      {
        "company": "Padaria",
        "email": "marina@example.com",
        "name": "Marina Silva",
        "phone": "",
        "pk": 2
      },
      {
        "company": "",
        "email": "",
        "name": "Ana Souza",
        "phone": "",
        "pk": 1
      }
    ],
    "page": "abc",
    "q": "  MARINA  "
  },
  "output": {
    "has_next": false,
    "has_previous": false,
    "next_page": null,
    "page_effective": 1,
    "per_page": 50,
    "prev_page": null,
    "q": "MARINA",
    "results": [
      {
        "company": "Padaria",
        "email": "marina@example.com",
        "name": "Marina Silva",
        "phone": "",
        "pk": 2
      }
    ],
    "total_count": 1,
    "total_pages": 1
  }
}
```

Public regression tests: `crm/test_community_contact_list_pagination.py`.


<!-- community-core:record-delete-preview -->
### Record delete impact preview core

Lets the Portuguese self-hosted CRM preview confirm-delete impact for companies, contacts, deals and tasks from pure JSON without database reads. It counts linked rows preserved by SET_NULL clearing so callers can explain that deleting one record never removes linked records. Ownership filtering stays with the caller.

Reusable deterministic JSON core: `crm/features/record_delete_preview.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) -> dict as a pure deterministic function with no I/O, env, time, randomness, callbacks or dependencies. Input payload must be an object with required key target as object and optional keys contacts list default empty, deals list default empty, tasks list default empty; extra keys ignored. Target must be an object with kind str one of company, contact, deal, task and pk int 1 to 9007199254740991 with booleans rejected; extra keys ignored. Each contact must be an object with pk int 1 to 9007199254740991 with booleans rejected and company_pk int 1 to 9007199254740991 or None with booleans rejected and missing means None; extra keys ignored. Each deal must be an object with pk int 1 to 9007199254740991 with booleans rejected and company_pk int 1 to 9007199254740991 or None with booleans rejected and missing means None and contact_pk int 1 to 9007199254740991 or None with booleans rejected and missing means None; extra keys ignored. Each task must be an object with pk int 1 to 9007199254740991 with booleans rejected and deal_pk int 1 to 9007199254740991 or None with booleans rejected and missing means None; extra keys ignored. Reject with ValueError if payload is not an object, target missing or malformed, contacts or deals or tasks are not lists, any list length over 2000, or any entry malformed. Uses only plain functions and immutable literal module constants with local mutable containers. Steps: 1 Preserve inputs without mutation. 2 If target kind is company collect contact pks where company_pk equals target pk and deal pks where company_pk equals target pk, deduplicate with local set then sort ascending; affected tasks empty. 3 If target kind is contact collect deal pks where contact_pk equals target pk, deduplicate then sort ascending; affected contacts and tasks empty. 4 If target kind is deal collect task pks where deal_pk equals target pk, deduplicate then sort ascending; affected contacts and deals empty. 5 If target kind is task all affected lists empty. 6 Build affected with contacts list of int plus deals list of int plus tasks list of int, all sorted ascending. 7 Build counts with contacts int plus deals int plus tasks int plus total int sum. 8 Set preserves_linked true always because Company and Contact and Deal links use SET_NULL clearing and deletion never removes linked rows. Returns dict with target kind plus pk, affected contacts plus deals plus tasks, counts contacts plus deals plus tasks plus total, preserves_linked bool true. Raises ValueError on malformed types or limit violations. Caller must pre-filter contacts and deals and tasks to current account and enforce ownership of target; function does no ownership check, DB query, CSV handling, or clock read and never mutates inputs. Preview only, not deletion or history editing or sharing proof.

Examples (JSON input and expected output):

```json
{
  "input": {
    "contacts": [
      {
        "company_pk": 7,
        "pk": 1
      },
      {
        "company_pk": 8,
        "pk": 2
      },
      {
        "company_pk": null,
        "pk": 3
      }
    ],
    "deals": [
      {
        "company_pk": 7,
        "contact_pk": null,
        "pk": 10
      },
      {
        "company_pk": 8,
        "contact_pk": null,
        "pk": 11
      }
    ],
    "target": {
      "kind": "company",
      "pk": 7
    },
    "tasks": [
      {
        "deal_pk": 10,
        "pk": 20
      }
    ]
  },
  "output": {
    "affected": {
      "contacts": [
        1
      ],
      "deals": [
        10
      ],
      "tasks": []
    },
    "counts": {
      "contacts": 1,
      "deals": 1,
      "tasks": 0,
      "total": 2
    },
    "preserves_linked": true,
    "target": {
      "kind": "company",
      "pk": 7
    }
  }
}
```

```json
{
  "input": {
    "contacts": [],
    "deals": [],
    "target": {
      "kind": "deal",
      "pk": 10
    },
    "tasks": [
      {
        "deal_pk": 10,
        "pk": 20
      },
      {
        "deal_pk": 11,
        "pk": 21
      },
      {
        "deal_pk": null,
        "pk": 22
      }
    ]
  },
  "output": {
    "affected": {
      "contacts": [],
      "deals": [],
      "tasks": [
        20
      ]
    },
    "counts": {
      "contacts": 0,
      "deals": 0,
      "tasks": 1,
      "total": 1
    },
    "preserves_linked": true,
    "target": {
      "kind": "deal",
      "pk": 10
    }
  }
}
```

```json
{
  "input": {
    "contacts": [],
    "deals": [
      {
        "company_pk": null,
        "contact_pk": 3,
        "pk": 10
      },
      {
        "company_pk": null,
        "contact_pk": 4,
        "pk": 11
      }
    ],
    "target": {
      "kind": "contact",
      "pk": 3
    },
    "tasks": []
  },
  "output": {
    "affected": {
      "contacts": [],
      "deals": [
        10
      ],
      "tasks": []
    },
    "counts": {
      "contacts": 0,
      "deals": 1,
      "tasks": 0,
      "total": 1
    },
    "preserves_linked": true,
    "target": {
      "kind": "contact",
      "pk": 3
    }
  }
}
```

Public regression tests: `crm/test_community_record_delete_preview.py`.


<!-- community-core:company-directory-snapshot -->
### Company directory snapshot core

Lets the Portuguese self-hosted CRM browse account companies with documented name search and stable name-then-pk ordering plus linked contact and deal counts from pure JSON without database reads. It mirrors the companies list ordering and preserves SET_NULL context that deleting a company never removes linked rows. Ownership filtering stays with the caller.

Reusable deterministic JSON core: `crm/features/company_directory_snapshot.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) -> dict as a pure deterministic function with no I/O, env, time, randomness, callbacks or dependencies. Input payload must be an object with optional keys: companies (list, default []), contacts (list, default []), deals (list, default []), q (str or None, default None); extra keys ignored. Each company must be an object with pk int 1 to 9007199254740991 (booleans rejected) and name str length 1 to 180; extra keys ignored. Each contact must be an object with pk int 1 to 9007199254740991 (booleans rejected) and company_pk int 1 to 9007199254740991 or None (booleans rejected, missing means None); extra keys ignored. Each deal must be an object with pk int 1 to 9007199254740991 (booleans rejected) and company_pk int 1 to 9007199254740991 or None (booleans rejected, missing means None); extra keys ignored. Reject with ValueError if payload is not an object, any list is not a list, any list length over 2000, any entry malformed, or q is not str or None. Uses only plain functions and immutable literal module constants with local mutable containers. Steps: 1 Preserve inputs without mutation. 2 Normalize q to empty when missing or None else strip then first 200 characters; when empty keep all companies else keep only companies where normalized casefold is substring of name casefold. 3 Sort kept companies by name Unicode codepoint then pk ascending. 4 For each kept company count contacts where company_pk equals company pk and deals where company_pk equals company pk. 5 Build results copying only pk, name plus contact_count int plus deal_count int. Returns dict with q normalized str, total_count int, results list. Raises ValueError on malformed types or limit violations. Caller must pre-filter companies, contacts and deals to current account; function does no ownership check, DB query, CSV handling, or clock read and never mutates inputs. Application/UI integration is outside this change. Read-only snapshot only, not deletion or sharing proof.

Examples (JSON input and expected output):

```json
{
  "input": {
    "companies": [
      {
        "name": "Padaria Sol",
        "pk": 2
      },
      {
        "name": "Mercado Lima",
        "pk": 1
      }
    ],
    "contacts": [
      {
        "company_pk": 1,
        "pk": 10
      },
      {
        "company_pk": 1,
        "pk": 11
      },
      {
        "company_pk": 2,
        "pk": 12
      }
    ],
    "deals": [
      {
        "company_pk": 1,
        "pk": 5
      }
    ],
    "q": "  mercado "
  },
  "output": {
    "q": "mercado",
    "results": [
      {
        "contact_count": 2,
        "deal_count": 1,
        "name": "Mercado Lima",
        "pk": 1
      }
    ],
    "total_count": 1
  }
}
```

```json
{
  "input": {
    "companies": [
      {
        "name": "Beta",
        "pk": 1
      },
      {
        "name": "Alfa",
        "pk": 2
      }
    ],
    "contacts": [],
    "deals": [],
    "q": null
  },
  "output": {
    "q": "",
    "results": [
      {
        "contact_count": 0,
        "deal_count": 0,
        "name": "Alfa",
        "pk": 2
      },
      {
        "contact_count": 0,
        "deal_count": 0,
        "name": "Beta",
        "pk": 1
      }
    ],
    "total_count": 2
  }
}
```

Public regression tests: `crm/test_community_company_directory_snapshot.py`.


<!-- community-core:dashboard-snapshot -->
### Dashboard snapshot core

Lets the Portuguese self-hosted CRM show dashboard counts for open opportunities and due follow-up tasks from pure JSON without database or clock reads. It mirrors Deal stages and Task due dates with a caller-supplied today, keeping ownership filtering with the caller.

Reusable deterministic JSON core: `crm/features/dashboard_snapshot.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) -> dict as a pure deterministic function with no I/O, env, time, randomness, callbacks or dependencies. Input payload must be an object with required key today as str YYYY-MM-DD valid calendar date including leap-year February 29 and optional keys deals (list, default empty) and tasks (list, default empty); extra keys ignored. Each deal must be an object with pk int 1 to 9007199254740991 with booleans rejected, stage str one of new, qualified, proposal, won, lost, value str as decimal digits with optional dot and one or two fraction digits, no leading zeros unless zero itself, and total cents at most 99999999999999; extra keys ignored. Each task must be an object with pk int 1 to 9007199254740991 with booleans rejected, due_date str YYYY-MM-DD valid calendar date including leap-year February 29, completed bool strictly; extra keys ignored. Reject with ValueError if payload is not an object, today missing or malformed, deals or tasks are not lists, either length over 2000, or any entry malformed. Uses only plain functions and immutable literal module constants with local mutable containers. Steps: 1 Preserve inputs without mutation. 2 Validate today and each due_date as calendar date. 3 Convert each value to integer cents as 100 to 10000 and 100.5 to 10050 and 100.05 to 10005 without float. 4 Define open stages as new, qualified and proposal; won and lost are closed. 5 Count deals_open_count where stage is open and deals_closed_count otherwise; sum open cents; format open totals as total_csv with exactly two decimals and no thousand separator and total_display as R$ with comma decimal and no thousand separator, zero as 0.00 and R$ 0,00. 6 For tasks count tasks_open_count where completed is false and tasks_completed_count where true; among open count overdue where due_date is less than today, due_today where equal, upcoming where greater, compared lexicographically equal to chronological for YYYY-MM-DD; set tasks_due_count to overdue plus due_today. Returns dict with today str, deals_open_count int, deals_closed_count int, deals_open_total_cents int, deals_open_total_csv str, deals_open_total_display str, tasks_open_count int, tasks_completed_count int, tasks_overdue_count int, tasks_due_today_count int, tasks_upcoming_count int, tasks_due_count int. Raises ValueError on malformed types, dates or limit violations. Caller must pre-filter deals and tasks to current account and map ValueError to user error; function does no ownership check, DB query, CSV handling, or clock read and never mutates inputs. Application and UI integration is outside this change. Read-only snapshot only, reflects current stage and value snapshot, not realized revenue, conversion, or future guarantee.

Examples (JSON input and expected output):

```json
{
  "input": {
    "deals": [
      {
        "pk": 1,
        "stage": "new",
        "value": "100.00"
      },
      {
        "pk": 2,
        "stage": "won",
        "value": "234.50"
      }
    ],
    "tasks": [
      {
        "completed": false,
        "due_date": "2026-03-09",
        "pk": 1
      },
      {
        "completed": false,
        "due_date": "2026-03-10",
        "pk": 2
      },
      {
        "completed": false,
        "due_date": "2026-03-11",
        "pk": 3
      },
      {
        "completed": true,
        "due_date": "2026-03-09",
        "pk": 4
      }
    ],
    "today": "2026-03-10"
  },
  "output": {
    "deals_closed_count": 1,
    "deals_open_count": 1,
    "deals_open_total_cents": 10000,
    "deals_open_total_csv": "100.00",
    "deals_open_total_display": "R$ 100,00",
    "tasks_completed_count": 1,
    "tasks_due_count": 2,
    "tasks_due_today_count": 1,
    "tasks_open_count": 3,
    "tasks_overdue_count": 1,
    "tasks_upcoming_count": 1,
    "today": "2026-03-10"
  }
}
```

```json
{
  "input": {
    "deals": [],
    "tasks": [],
    "today": "2024-02-29"
  },
  "output": {
    "deals_closed_count": 0,
    "deals_open_count": 0,
    "deals_open_total_cents": 0,
    "deals_open_total_csv": "0.00",
    "deals_open_total_display": "R$ 0,00",
    "tasks_completed_count": 0,
    "tasks_due_count": 0,
    "tasks_due_today_count": 0,
    "tasks_open_count": 0,
    "tasks_overdue_count": 0,
    "tasks_upcoming_count": 0,
    "today": "2024-02-29"
  }
}
```

```json
{
  "input": {
    "deals": [
      {
        "pk": 10,
        "stage": "qualified",
        "value": "100.5"
      },
      {
        "pk": 11,
        "stage": "proposal",
        "value": "1134.05"
      }
    ],
    "tasks": [
      {
        "completed": false,
        "due_date": "2026-01-15",
        "pk": 5
      }
    ],
    "today": "2026-01-15"
  },
  "output": {
    "deals_closed_count": 0,
    "deals_open_count": 2,
    "deals_open_total_cents": 123455,
    "deals_open_total_csv": "1234.55",
    "deals_open_total_display": "R$ 1234,55",
    "tasks_completed_count": 0,
    "tasks_due_count": 1,
    "tasks_due_today_count": 1,
    "tasks_open_count": 1,
    "tasks_overdue_count": 0,
    "tasks_upcoming_count": 0,
    "today": "2026-01-15"
  }
}
```

Public regression tests: `crm/test_community_dashboard_snapshot.py`.


<!-- community-core:pipeline-board-snapshot -->
### Pipeline board snapshot core

Lets the Portuguese self-hosted CRM render the documented five-stage sales pipeline board from pure JSON without database reads. It groups caller-supplied opportunities by current stage with Portuguese labels and per-column plus grand value totals, keeping ownership filtering with the caller.

Reusable deterministic JSON core: `crm/features/pipeline_board_snapshot.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) -> dict as a pure deterministic function with no I/O, env, time, randomness, callbacks or dependencies. Input payload must be an object with optional key deals (list, default []); extra keys ignored. Each deal must be an object with pk int 1 to 9007199254740991 (booleans rejected), title str length 1 to 180, stage str one of new, qualified, proposal, won, lost, value str decimal digits with optional dot and one or two fraction digits, no leading zeros unless zero itself, and total cents at most 99999999999999; extra keys ignored. Reject with ValueError if payload is not an object, deals is not a list, length over 2000, or any entry malformed. Uses only plain functions and immutable literal module constants with local mutable containers. Steps: 1 Preserve inputs without mutation. 2 Validate each deal and convert each value to integer cents (100 to 10000, 100.5 to 10050, 100.05 to 10005) without float. 3 Partition all deals into five columns in fixed order new, qualified, proposal, won, lost, retaining input order within each column; no date filtering, every supplied deal appears in exactly one column. 4 For each deal build pk, title, stage, value_cents int, value_csv str exactly two decimals no thousand separator, value_display str R$ plus space plus comma decimal no thousand separator. 5 For each column build label str Portuguese Novo, Qualificado, Proposta, Ganho, Perdido, count int, total_cents int, total_csv str, total_display str, deals list with zero as 0.00 and R$ 0,00. 6 Build grand count, total_cents, total_csv, total_display. Returns dict with deal_count int, columns object, grand object. Raises ValueError on malformed types or limit violations. Caller must pre-filter deals to current account and map ValueError to user error; function does no ownership check, DB query, CSV handling, or clock read and never mutates inputs. Application and UI integration is outside this change. Read-only snapshot only, reflects current stage and value snapshot, not history, realized revenue, conversion, or future guarantee.

Examples (JSON input and expected output):

```json
{
  "input": {
    "deals": [
      {
        "pk": 1,
        "stage": "new",
        "title": "Padaria",
        "value": "100.00"
      },
      {
        "pk": 2,
        "stage": "won",
        "title": "Mercado",
        "value": "234.50"
      }
    ]
  },
  "output": {
    "columns": {
      "lost": {
        "count": 0,
        "deals": [],
        "label": "Perdido",
        "total_cents": 0,
        "total_csv": "0.00",
        "total_display": "R$ 0,00"
      },
      "new": {
        "count": 1,
        "deals": [
          {
            "pk": 1,
            "stage": "new",
            "title": "Padaria",
            "value_cents": 10000,
            "value_csv": "100.00",
            "value_display": "R$ 100,00"
          }
        ],
        "label": "Novo",
        "total_cents": 10000,
        "total_csv": "100.00",
        "total_display": "R$ 100,00"
      },
      "proposal": {
        "count": 0,
        "deals": [],
        "label": "Proposta",
        "total_cents": 0,
        "total_csv": "0.00",
        "total_display": "R$ 0,00"
      },
      "qualified": {
        "count": 0,
        "deals": [],
        "label": "Qualificado",
        "total_cents": 0,
        "total_csv": "0.00",
        "total_display": "R$ 0,00"
      },
      "won": {
        "count": 1,
        "deals": [
          {
            "pk": 2,
            "stage": "won",
            "title": "Mercado",
            "value_cents": 23450,
            "value_csv": "234.50",
            "value_display": "R$ 234,50"
          }
        ],
        "label": "Ganho",
        "total_cents": 23450,
        "total_csv": "234.50",
        "total_display": "R$ 234,50"
      }
    },
    "deal_count": 2,
    "grand": {
      "count": 2,
      "total_cents": 33450,
      "total_csv": "334.50",
      "total_display": "R$ 334,50"
    }
  }
}
```

```json
{
  "input": {},
  "output": {
    "columns": {
      "lost": {
        "count": 0,
        "deals": [],
        "label": "Perdido",
        "total_cents": 0,
        "total_csv": "0.00",
        "total_display": "R$ 0,00"
      },
      "new": {
        "count": 0,
        "deals": [],
        "label": "Novo",
        "total_cents": 0,
        "total_csv": "0.00",
        "total_display": "R$ 0,00"
      },
      "proposal": {
        "count": 0,
        "deals": [],
        "label": "Proposta",
        "total_cents": 0,
        "total_csv": "0.00",
        "total_display": "R$ 0,00"
      },
      "qualified": {
        "count": 0,
        "deals": [],
        "label": "Qualificado",
        "total_cents": 0,
        "total_csv": "0.00",
        "total_display": "R$ 0,00"
      },
      "won": {
        "count": 0,
        "deals": [],
        "label": "Ganho",
        "total_cents": 0,
        "total_csv": "0.00",
        "total_display": "R$ 0,00"
      }
    },
    "deal_count": 0,
    "grand": {
      "count": 0,
      "total_cents": 0,
      "total_csv": "0.00",
      "total_display": "R$ 0,00"
    }
  }
}
```

```json
{
  "input": {
    "deals": [
      {
        "company": "Extra",
        "pk": 10,
        "stage": "proposal",
        "title": "B",
        "value": "100"
      },
      {
        "pk": 9,
        "stage": "proposal",
        "title": "A",
        "value": "100.5"
      },
      {
        "pk": 11,
        "stage": "proposal",
        "title": "C",
        "value": "100.05"
      }
    ]
  },
  "output": {
    "columns": {
      "lost": {
        "count": 0,
        "deals": [],
        "label": "Perdido",
        "total_cents": 0,
        "total_csv": "0.00",
        "total_display": "R$ 0,00"
      },
      "new": {
        "count": 0,
        "deals": [],
        "label": "Novo",
        "total_cents": 0,
        "total_csv": "0.00",
        "total_display": "R$ 0,00"
      },
      "proposal": {
        "count": 3,
        "deals": [
          {
            "pk": 10,
            "stage": "proposal",
            "title": "B",
            "value_cents": 10000,
            "value_csv": "100.00",
            "value_display": "R$ 100,00"
          },
          {
            "pk": 9,
            "stage": "proposal",
            "title": "A",
            "value_cents": 10050,
            "value_csv": "100.50",
            "value_display": "R$ 100,50"
          },
          {
            "pk": 11,
            "stage": "proposal",
            "title": "C",
            "value_cents": 10005,
            "value_csv": "100.05",
            "value_display": "R$ 100,05"
          }
        ],
        "label": "Proposta",
        "total_cents": 30055,
        "total_csv": "300.55",
        "total_display": "R$ 300,55"
      },
      "qualified": {
        "count": 0,
        "deals": [],
        "label": "Qualificado",
        "total_cents": 0,
        "total_csv": "0.00",
        "total_display": "R$ 0,00"
      },
      "won": {
        "count": 0,
        "deals": [],
        "label": "Ganho",
        "total_cents": 0,
        "total_csv": "0.00",
        "total_display": "R$ 0,00"
      }
    },
    "deal_count": 3,
    "grand": {
      "count": 3,
      "total_cents": 30055,
      "total_csv": "300.55",
      "total_display": "R$ 300,55"
    }
  }
}
```

Public regression tests: `crm/test_community_pipeline_board_snapshot.py`.


<!-- community-core:task-draft-validator -->
### Follow-up task draft validator core

Lets the Portuguese self-hosted CRM validate follow-up task drafts from pure JSON without database or clock reads. It mirrors Task title, due_date, completed and optional Deal linkage so callers can explain required fields and bad dates before saving. Ownership filtering and persistence stay with the caller.

Reusable deterministic JSON core: `crm/features/task_draft_validator.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) -> dict as a pure deterministic function with no I/O, env, time, randomness, callbacks or dependencies. Input payload must be an object; extra keys ignored. Optional keys: title, due_date, completed (default False), deal_pk (default None). Uses only plain functions and immutable literal module constants with local mutable containers. Steps: 1 Preserve inputs without mutation. 2 Reject with ValueError if payload is not an object. 3 Validate title: if missing or None then error "title is required"; if not str then error "title must be a string"; else strip space, TAB, LF, CR from both ends and if empty then error "title is required"; if length over 180 then error "title must be at most 180 characters"; else keep trimmed title. 4 Validate due_date: if missing or None or empty string then error "due_date is required"; else must be str length 10 YYYY-MM-DD with valid calendar month and day including Feb 29 only on leap years divisible by 400 or divisible by 4 and not by 100 else error "due_date must be YYYY-MM-DD valid calendar date". 5 Validate completed: if missing then False; if not strictly bool (reject ints) then error "completed must be a boolean". 6 Validate deal_pk: if missing or None then null; if bool or not int or outside 1 to 9007199254740991 then error "deal_pk must be an integer 1 to 9007199254740991 or null". 7 If any errors return {valid False, errors object with failing keys, normalized null}. 8 Else return {valid True, errors {}, normalized {title trimmed, due_date string, completed bool, deal_pk int or null}}. Caller must pre-filter deal_pk to current account, enforce Task ownership and handle persistence; function does no ownership check, DB query, CSV handling, or clock read and never mutates inputs. Read-only draft check only, not history, conversion, or guarantee.

Examples (JSON input and expected output):

```json
{
  "input": {
    "completed": false,
    "deal_pk": null,
    "due_date": "2026-03-10",
    "title": "Retornar para Marina"
  },
  "output": {
    "errors": {},
    "normalized": {
      "completed": false,
      "deal_pk": null,
      "due_date": "2026-03-10",
      "title": "Retornar para Marina"
    },
    "valid": true
  }
}
```

```json
{
  "input": {
    "completed": false,
    "due_date": "2026-02-30",
    "title": "  "
  },
  "output": {
    "errors": {
      "due_date": "due_date must be YYYY-MM-DD valid calendar date",
      "title": "title is required"
    },
    "normalized": null,
    "valid": false
  }
}
```

```json
{
  "input": {
    "completed": 0,
    "deal_pk": 0,
    "due_date": "2024-02-29",
    "title": "Ligar amanha"
  },
  "output": {
    "errors": {
      "completed": "completed must be a boolean",
      "deal_pk": "deal_pk must be an integer 1 to 9007199254740991 or null"
    },
    "normalized": null,
    "valid": false
  }
}
```

Public regression tests: `crm/test_community_task_draft_validator.py`.


<!-- community-core:deal-draft-validator -->
### Sales opportunity draft validator core

Lets the Portuguese self-hosted CRM validate sales opportunity drafts from pure JSON without database or clock reads. It mirrors Deal title, value, five documented stages, forecast date and optional company and contact links so callers can explain required fields and bad values before saving. Ownership filtering and persistence stay with the caller.

Reusable deterministic JSON core: `crm/features/deal_draft_validator.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) -> dict as a pure deterministic function with no I/O, env, time, randomness, callbacks or dependencies. Input payload must be an object; extra keys ignored. Optional keys: title, value (default "0.00"), stage (default "new"), expected_close (default None), company_pk (default None), contact_pk (default None). Uses only plain functions and immutable literal module constants with local mutable containers. Steps: 1 Preserve inputs without mutation. 2 Reject with ValueError if payload is not an object. 3 Validate title: if missing or None then error "title is required"; if not str then error "title must be a string"; else trim leading/trailing space, TAB, LF, CR and if empty then error "title is required"; if length over 180 then error "title must be at most 180 characters"; else keep trimmed title. 4 Validate value: if missing then use "0.00"; if not str then error "value must be a decimal string"; else must match ^(0|[1-9][0-9]*)(\.[0-9]{1,2})?$ else error "value must be a decimal string"; convert to integer cents without float ("100"->10000, "100.5"->10050, "100.05"->10005) and if total cents over 99999999999999 then error "value is too large"; else keep canonical two-decimal string and cents. 5 Validate stage: if missing then "new"; if not str then error "stage must be one of new, qualified, proposal, won, lost"; else must be one of new, qualified, proposal, won, lost else same error; else keep. 6 Validate expected_close: if missing or None or "" then null; else must be str length 10 YYYY-MM-DD with valid calendar month and day including Feb 29 only on leap years divisible by 400 or divisible by 4 and not by 100 else error "expected_close must be YYYY-MM-DD valid calendar date"; else keep string. 7 Validate company_pk and contact_pk each: if missing or None then null; if bool or not int or outside 1 to 9007199254740991 then error with field name plus " must be an integer 1 to 9007199254740991 or null"; else keep. 8 If any errors return {valid False, errors object with failing keys, normalized null}. 9 Else return {valid True, errors {}, normalized {title trimmed, value canonical two decimals, value_cents int, stage str, expected_close str or null, company_pk int or null, contact_pk int or null}}. Raises ValueError only when payload is not an object. Caller must pre-filter company_pk and contact_pk to current account, enforce Deal ownership and handle persistence; function does no ownership check, DB query, CSV handling, or clock read and never mutates inputs. Read-only draft check only, reflects current vocabulary snapshot, not history, realized revenue, conversion, or future guarantee. Application and UI integration is outside this change.

Examples (JSON input and expected output):

```json
{
  "input": {
    "company_pk": null,
    "contact_pk": null,
    "expected_close": null,
    "stage": "new",
    "title": " Padaria ",
    "value": "100.5"
  },
  "output": {
    "errors": {},
    "normalized": {
      "company_pk": null,
      "contact_pk": null,
      "expected_close": null,
      "stage": "new",
      "title": "Padaria",
      "value": "100.50",
      "value_cents": 10050
    },
    "valid": true
  }
}
```

```json
{
  "input": {
    "company_pk": 0,
    "contact_pk": false,
    "expected_close": "2026-02-30",
    "stage": "closed",
    "title": "",
    "value": "abc"
  },
  "output": {
    "errors": {
      "company_pk": "company_pk must be an integer 1 to 9007199254740991 or null",
      "contact_pk": "contact_pk must be an integer 1 to 9007199254740991 or null",
      "expected_close": "expected_close must be YYYY-MM-DD valid calendar date",
      "stage": "stage must be one of new, qualified, proposal, won, lost",
      "title": "title is required",
      "value": "value must be a decimal string"
    },
    "normalized": null,
    "valid": false
  }
}
```

```json
{
  "input": {
    "title": "Mercado"
  },
  "output": {
    "errors": {},
    "normalized": {
      "company_pk": null,
      "contact_pk": null,
      "expected_close": null,
      "stage": "new",
      "title": "Mercado",
      "value": "0.00",
      "value_cents": 0
    },
    "valid": true
  }
}
```

Public regression tests: `crm/test_community_deal_draft_validator.py`.


<!-- community-core:company-draft-validator -->
### Company draft validator core

Lets the Portuguese self-hosted CRM validate company drafts from pure JSON without database reads. It mirrors Company name, website and notes so callers can explain required fields, bad URLs and overlong text before saving. Ownership filtering and persistence stay with the caller.

Reusable deterministic JSON core: `crm/features/company_draft_validator.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) -> dict as a pure deterministic function with no I/O, env, time, randomness, callbacks or dependencies. Input payload must be an object; extra keys ignored. Optional keys: name, website (default ""), notes (default ""). Uses only plain functions and immutable literal module constants with local mutable containers. Steps: 1 Preserve inputs without mutation. 2 Reject with ValueError if payload is not an object. 3 Validate name: if missing or None then error "name is required"; if not str then error "name must be a string"; else trim leading/trailing space, TAB, LF, CR and if empty then error "name is required"; if length over 180 then error "name must be at most 180 characters"; else keep trimmed name. 4 Validate website: if missing or None then ""; if not str then error "website must be a valid URL or empty"; else trim leading/trailing space, TAB, LF, CR and if empty then ""; else if length over 200 or not matching ^https?://[^\s]+\.[^\s]+$ then error "website must be a valid URL or empty"; else keep trimmed website. 5 Validate notes: if missing or None then ""; if not str then error "notes must be a string"; if length over 10000 then error "notes must be at most 10000 characters"; else keep unchanged. 6 If any errors return {valid False, errors object with failing keys, normalized null}. 7 Else return {valid True, errors {}, normalized {name trimmed, website trimmed or "", notes str}}. Raises ValueError only when payload is not an object. Caller must pre-filter to current account, enforce Company ownership and handle persistence; function does no ownership check, DB query, CSV handling, or clock read and never mutates inputs. Read-only draft check only, reflects current vocabulary snapshot, not history, conversion, or future guarantee. Application and UI integration is outside this change.

Examples (JSON input and expected output):

```json
{
  "input": {
    "name": " Padaria Pao Novo ",
    "notes": "Fictional example",
    "website": "https://exemplo.com"
  },
  "output": {
    "errors": {},
    "normalized": {
      "name": "Padaria Pao Novo",
      "notes": "Fictional example",
      "website": "https://exemplo.com"
    },
    "valid": true
  }
}
```

```json
{
  "input": {
    "name": "   ",
    "notes": 123,
    "website": "exemplo"
  },
  "output": {
    "errors": {
      "name": "name is required",
      "notes": "notes must be a string",
      "website": "website must be a valid URL or empty"
    },
    "normalized": null,
    "valid": false
  }
}
```

Public regression tests: `crm/test_community_company_draft_validator.py`.


<!-- community-core:company-duplicate-finder -->
### Company duplicate finder core

Lets the Portuguese self-hosted CRM preview ambiguous company names from pure JSON without database or clock reads. It groups owner-scoped companies by trimmed casefolded name so callers can warn before contact CSV import blocks on ambiguous exact names. Ownership filtering and merging stay with the caller.

Reusable deterministic JSON core: `crm/features/company_duplicate_finder.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) -> dict as a pure deterministic function with no I/O, env, time, randomness, callbacks or dependencies. Uses only plain functions and immutable literal module constants with local mutable containers. Input payload must be an object; extra keys ignored. Optional key companies (list, default []). Preserve inputs without mutation. Validate payload is object else ValueError. Validate companies is list max 5000 else ValueError; each entry must be an object with pk int excluding booleans from 1 to 9007199254740991 else ValueError and name str max 180 else ValueError; extra keys ignored; pk values must be unique else ValueError; name stripped of leading and trailing space TAB LF CR must be non-empty else ValueError. Steps: 1 Normalize each name by stripping leading and trailing space TAB LF CR then applying casefold to form key. 2 Group entries by key. 3 Keep only groups with count greater than 1. 4 Sort groups by key code-point order; sort companies within each group by pk ascending each as {pk, name} preserving exact original name. Returns dict with group_count int equal to groups length and groups list each {key str, count int, companies list}. Raises ValueError on malformed types, empty names, duplicate pk, or oversized list. Caller must pre-filter companies to the current account and map ValueError to user error; function does no ownership check, DB query, CSV handling, or clock read and never mutates inputs. Read-only duplicate preview only, not merge, delete, creation, or import resolution; exact-name import matching stays with the caller. Application and UI integration is outside this change.

Examples (JSON input and expected output):

```json
{
  "input": {
    "companies": [
      {
        "name": "Acme",
        "pk": 1
      },
      {
        "name": " acme ",
        "pk": 2
      },
      {
        "name": "Beta",
        "pk": 3
      }
    ]
  },
  "output": {
    "group_count": 1,
    "groups": [
      {
        "companies": [
          {
            "name": "Acme",
            "pk": 1
          },
          {
            "name": " acme ",
            "pk": 2
          }
        ],
        "count": 2,
        "key": "acme"
      }
    ]
  }
}
```

```json
{
  "input": {
    "companies": [
      {
        "name": "Padaria",
        "pk": 1
      },
      {
        "name": "Mercado",
        "pk": 2
      }
    ]
  },
  "output": {
    "group_count": 0,
    "groups": []
  }
}
```

```json
{
  "input": {
    "companies": [
      {
        "name": "SÃO PAULO",
        "pk": 5
      },
      {
        "name": "são paulo",
        "pk": 6
      }
    ]
  },
  "output": {
    "group_count": 1,
    "groups": [
      {
        "companies": [
          {
            "name": "SÃO PAULO",
            "pk": 5
          },
          {
            "name": "são paulo",
            "pk": 6
          }
        ],
        "count": 2,
        "key": "são paulo"
      }
    ]
  }
}
```

Public regression tests: `crm/test_community_company_duplicate_finder.py`.


<!-- community-core:br-currency-input-parser -->
### Brazilian currency input parser core

Lets the Portuguese self-hosted CRM parse user-typed Brazilian currency values from pure JSON without database or clock reads. It accepts an optional R$ prefix, dot thousand separators with comma decimals or plain dot decimals, and returns integer cents plus HTML and CSV strings so callers can validate opportunity values predictably. Ownership, persistence and formatting decisions stay with the caller.

Reusable deterministic JSON core: `crm/features/br_currency_input_parser.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) -> dict as a pure deterministic function with no I/O, env, time, randomness, callbacks or dependencies. Uses only plain functions and immutable literal module constants with local mutable containers. Input payload must be an object; extra keys ignored. Required key raw must be a string else ValueError. Preserve inputs without mutation. Validate raw length at most 64 else ValueError. Strip leading and trailing space TAB LF CR; if empty raise ValueError. If stripped starts with R$ remove those two characters then strip leading and trailing space TAB LF CR again; if empty raise ValueError. Let s be the remainder. Reject if s contains space TAB LF CR inside else ValueError. Reject if s contains any character other than digits dot comma else ValueError. If s contains comma then it must contain exactly one comma else ValueError; split at comma into int_part and frac_part; frac_part must be one or two digits else ValueError; int_part must be non-empty else ValueError; int_part must match plain integer or Brazilian thousand grouping with dot every three digits else ValueError. If s has no comma then it must contain at most one dot else ValueError; if dot present split into int_part and frac_part with frac_part one or two digits else ValueError; int_part must be 0 or non-zero-leading digits else ValueError; no dot thousand separators allowed in this branch. Remove dots from int_part to obtain digit string; it must be 0 or start with 1-9 with length at most 12 else ValueError. Compute cents without float as integer digits times 100 plus frac padded right to two digits; if cents exceeds 99999999999999 raise ValueError. Build value_csv as integer part dot two digits and value_display as R$ space integer part comma two digits with no thousand separator and zero as 0.00 and R$ 0,00. Returns dict with cents int, value_csv string, value_display string. Raises ValueError on malformed types, empty input, bad characters, bad grouping, bad decimals or oversized length or value. Caller must map ValueError to user error and handle ownership, persistence and localization; function does no ownership check, DB query, CSV file handling or clock read and never mutates inputs. Syntax parsing only, not financial advice, conversion, creation or guarantee. Application and UI integration is outside this change.

Examples (JSON input and expected output):

```json
{
  "input": {
    "raw": "R$ 1.234,50"
  },
  "output": {
    "cents": 123450,
    "value_csv": "1234.50",
    "value_display": "R$ 1234,50"
  }
}
```

```json
{
  "input": {
    "raw": "100.5"
  },
  "output": {
    "cents": 10050,
    "value_csv": "100.50",
    "value_display": "R$ 100,50"
  }
}
```

```json
{
  "input": {
    "raw": "0"
  },
  "output": {
    "cents": 0,
    "value_csv": "0.00",
    "value_display": "R$ 0,00"
  }
}
```

Public regression tests: `crm/test_community_br_currency_input_parser.py`.


<!-- community-core:company-list-pagination -->
### Company list pagination core

Lets the Portuguese self-hosted CRM browse its own companies from pure JSON without database reads. It filters by normalized name query, orders by name then pk, and paginates fifty per page with Django get_page semantics so callers render stable lists. Ownership filtering stays with the caller.

Reusable deterministic JSON core: `crm/features/company_list_pagination.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) -> dict as a pure deterministic function with no I/O, env, time, randomness, callbacks or dependencies. Uses only plain functions and immutable literal module constants with local mutable containers. Input payload must be an object; extra keys ignored. Optional companies list default []; optional q string or None default None; optional page string, integer, or None default None. Preserve inputs without mutation. Validate payload object else ValueError. Validate companies list max 5000 else ValueError. Each entry object else ValueError with pk int excluding booleans 1 to 9007199254740991 else ValueError and name str max 180 else ValueError; extra keys ignored; duplicate pk raises ValueError. Validate q missing or None means empty else must be str max 5000 else ValueError; normalized as stripped space TAB LF CR truncated to 200 chars. Validate page missing or None means 1; int excluding booleans means that value; str stripped space TAB LF CR empty means 1 else all-digit optional minus integer parses else 1 for non-integer; other types raise ValueError. Steps: 1 Normalize q. 2 Filter by casefold substring of name when q non-empty else keep all. 3 Sort by name casefold then name then pk ascending. 4 Compute total_count and num_pages as max 1 of ceiling total over 50 with per_page 50; empty is page 1 of 1. 5 Resolve effective page: non-integer input means 1; integer less than 1 or greater than num_pages means num_pages else value. 6 Slice fifty records and map to pk and name copies. 7 Build flags has_previous, has_next, prev_page, next_page. Returns dict with q string, page int, per_page 50, num_pages int, total_count int, results list, has_previous bool, has_next bool, prev_page int or None, next_page int or None. Raises ValueError on malformed types, oversized lists, duplicate pks or bad page types. Caller must pre-filter companies to current account, map ValueError to user error and render navigation; function does no ownership check, DB query, CSV handling or clock read and never mutates inputs. Read-only list helper only, not creation, update, deletion or permission enforcement. Application and UI integration is outside this change.

Examples (JSON input and expected output):

```json
{
  "input": {
    "companies": [
      {
        "name": "Beta Mercado",
        "pk": 2
      },
      {
        "name": "Alfa Padaria",
        "pk": 1
      }
    ],
    "page": "1",
    "q": " padaria "
  },
  "output": {
    "has_next": false,
    "has_previous": false,
    "next_page": null,
    "num_pages": 1,
    "page": 1,
    "per_page": 50,
    "prev_page": null,
    "q": "padaria",
    "results": [
      {
        "name": "Alfa Padaria",
        "pk": 1
      }
    ],
    "total_count": 1
  }
}
```

```json
{
  "input": {
    "companies": [
      {
        "name": "Zeta",
        "pk": 3
      },
      {
        "name": "Alfa",
        "pk": 1
      },
      {
        "name": "alfa",
        "pk": 2
      }
    ],
    "page": 99,
    "q": ""
  },
  "output": {
    "has_next": false,
    "has_previous": false,
    "next_page": null,
    "num_pages": 1,
    "page": 1,
    "per_page": 50,
    "prev_page": null,
    "q": "",
    "results": [
      {
        "name": "Alfa",
        "pk": 1
      },
      {
        "name": "alfa",
        "pk": 2
      },
      {
        "name": "Zeta",
        "pk": 3
      }
    ],
    "total_count": 3
  }
}
```

Public regression tests: `crm/test_community_company_list_pagination.py`.


<!-- community-core:deal-list-pagination -->
### Deal list pagination core

Lets the Portuguese self-hosted CRM browse its own sales opportunities from pure JSON without database reads. It filters by pipeline stage and normalized title query, orders by title then pk, and paginates fifty per page with Django get_page semantics so callers render stable opportunity lists. Ownership filtering stays with the caller.

Reusable deterministic JSON core: `crm/features/deal_list_pagination.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) -> dict as a pure deterministic function with no I/O, env, time, randomness, callbacks or dependencies. Uses only plain functions and immutable literal module constants with local mutable containers. Input payload must be an object; extra keys ignored. Optional deals list default empty; optional q string or None default None; optional stage string or None default None; optional page string, integer, or None default None. Preserve inputs without mutation. Validate payload object else ValueError. Validate deals list max 5000 else ValueError. Each entry object else ValueError with pk int excluding booleans 1 to 9007199254740991 else ValueError and title str max 180 else ValueError and stage str one of new, qualified, proposal, won, lost else ValueError; extra keys ignored; duplicate pk raises ValueError. Validate q missing or None means empty else must be str max 5000 else ValueError; normalized as stripped space TAB LF CR truncated to 200 chars. Validate stage missing or None means all else must be str else ValueError; stripped space TAB LF CR empty or all means all else must be one of new, qualified, proposal, won, lost else ValueError. Validate page missing or None means 1; int excluding booleans means that value; str stripped space TAB LF CR empty means 1 else optional-minus all-digit integer parses else 1 for non-integer; other types raise ValueError. Steps: 1 Normalize q and stage. 2 Filter by stage when not all then by casefold substring of title when q non-empty else keep all. 3 Sort by title casefold then title then pk ascending. 4 Compute total_count and num_pages as max 1 of ceiling total over 50 with per_page 50; empty is page 1 of 1. 5 Resolve effective page: non-integer input means 1; integer less than 1 or greater than num_pages means num_pages else value. 6 Slice fifty records and map to pk, title and stage copies. 7 Build flags has_previous, has_next, prev_page, next_page. Returns dict with q string, stage string all or stage, page int, per_page 50, num_pages int, total_count int, results list, has_previous bool, has_next bool, prev_page int or None, next_page int or None. Raises ValueError on malformed types, oversized lists, duplicate pks or bad stage and page types. Caller must pre-filter deals to current account, map ValueError to user error and render navigation; function does no ownership check, DB query, CSV handling or clock read and never mutates inputs. Read-only list helper only, not creation, update, deletion or permission enforcement. Application and UI integration is outside this change.

Examples (JSON input and expected output):

```json
{
  "input": {
    "deals": [
      {
        "pk": 1,
        "stage": "new",
        "title": "Padaria"
      },
      {
        "pk": 2,
        "stage": "won",
        "title": "Mercado"
      }
    ],
    "page": 1,
    "q": "",
    "stage": "all"
  },
  "output": {
    "has_next": false,
    "has_previous": false,
    "next_page": null,
    "num_pages": 1,
    "page": 1,
    "per_page": 50,
    "prev_page": null,
    "q": "",
    "results": [
      {
        "pk": 2,
        "stage": "won",
        "title": "Mercado"
      },
      {
        "pk": 1,
        "stage": "new",
        "title": "Padaria"
      }
    ],
    "stage": "all",
    "total_count": 2
  }
}
```

```json
{
  "input": {
    "deals": [
      {
        "pk": 1,
        "stage": "new",
        "title": "Padaria Centro"
      },
      {
        "pk": 2,
        "stage": "qualified",
        "title": "Padaria Norte"
      },
      {
        "pk": 3,
        "stage": "new",
        "title": "Mercado Sul"
      }
    ],
    "page": 1,
    "q": "padaria",
    "stage": "new"
  },
  "output": {
    "has_next": false,
    "has_previous": false,
    "next_page": null,
    "num_pages": 1,
    "page": 1,
    "per_page": 50,
    "prev_page": null,
    "q": "padaria",
    "results": [
      {
        "pk": 1,
        "stage": "new",
        "title": "Padaria Centro"
      }
    ],
    "stage": "new",
    "total_count": 1
  }
}
```

```json
{
  "input": {
    "deals": [],
    "page": 99,
    "q": "zzz",
    "stage": "all"
  },
  "output": {
    "has_next": false,
    "has_previous": false,
    "next_page": null,
    "num_pages": 1,
    "page": 1,
    "per_page": 50,
    "prev_page": null,
    "q": "zzz",
    "results": [],
    "stage": "all",
    "total_count": 0
  }
}
```

Public regression tests: `crm/test_community_deal_list_pagination.py`.


<!-- community-core:export-filename-builder -->
### CSV export filename builder core

Lets the Portuguese self-hosted CRM build safe ASCII download filenames for contact, company and pipeline CSV exports from pure JSON without database, files or clock reads. It normalizes accents, case and symbols deterministically so callers name only current-account exports. Ownership filtering stays with the caller.

Reusable deterministic JSON core: `crm/features/export_filename_builder.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) -> dict as a pure deterministic function with no I/O, env, time, randomness, callbacks or dependencies. Uses only plain functions and immutable literal module constants with local mutable containers. Input payload must be an object; extra keys ignored. Optional base str or None default None meaning export; optional tag str or None default None meaning no tag; optional ext str or None default None meaning csv. Preserve inputs without mutation. Validate payload object else ValueError. Validate base missing or None means raw export else must be str max 500 else ValueError; strip space TAB LF CR and if empty use export. Validate tag missing or None means no tag else must be str max 500 else ValueError; stripped space TAB LF CR empty means no tag. Validate ext missing or None means csv else must be str else ValueError; stripped casefolded must equal csv else ValueError. Sanitize helper: NFKD normalize via unicodedata, casefold, drop Mn combining marks, map via re sub [^a-z0-9]+ to single hyphen, strip leading trailing hyphen, truncate base_slug to 30 and tag_slug to 40 then strip hyphens again; empty base_slug falls back to export and empty tag_slug means no tag. Steps: 1 Normalize raw base and tag and ext. 2 Sanitize to base_slug and tag_slug. 3 Build filename as base_slug plus hyphen tag_slug when present plus dot csv. Returns dict with filename str, base_slug str, tag_slug str empty when absent, ext csv. Raises ValueError on malformed payload, bad types, oversized strings or unsupported ext. Caller must pre-filter rows to current account, choose base and tag vocabularies, map ValueError to user error and attach Content-Disposition; function does no ownership check, DB query, file I/O or clock read and never mutates inputs. Naming helper only, not creation, update, deletion or permission enforcement. Application and UI integration is outside this change.

Examples (JSON input and expected output):

```json
{
  "input": {
    "base": "Contatos",
    "tag": "São Marina"
  },
  "output": {
    "base_slug": "contatos",
    "ext": "csv",
    "filename": "contatos-sao-marina.csv",
    "tag_slug": "sao-marina"
  }
}
```

```json
{
  "input": {
    "base": "Pipeline",
    "tag": "2026-01-01 a 2026-01-31"
  },
  "output": {
    "base_slug": "pipeline",
    "ext": "csv",
    "filename": "pipeline-2026-01-01-a-2026-01-31.csv",
    "tag_slug": "2026-01-01-a-2026-01-31"
  }
}
```

```json
{
  "input": {},
  "output": {
    "base_slug": "export",
    "ext": "csv",
    "filename": "export.csv",
    "tag_slug": ""
  }
}
```

Public regression tests: `crm/test_community_export_filename_builder.py`.


<!-- community-core:deal-stage-transition-guard -->
### Deal stage transition guard core

Lets the Portuguese self-hosted CRM validate five-stage pipeline moves from pure JSON without database or clock reads. It allows open-stage progress and closing to won or lost, keeps won and lost terminal, and reports noop, close and blocked cases so callers share form validation. Ownership filtering stays with the caller.

Reusable deterministic JSON core: `crm/features/deal_stage_transition_guard.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) -> dict as a pure deterministic function with no I/O, env, time, randomness, callbacks or dependencies. Uses only plain functions and immutable literal module constants with local mutable containers. Input payload must be an object; extra keys ignored. Required keys current_stage str and next_stage str each one of new, qualified, proposal, won, lost else ValueError. Preserve inputs without mutation. Define OPEN as new, qualified, proposal and CLOSED as won, lost. Steps: 1 Validate payload object and both stages are exact strings in set. 2 Set changed false when current_stage equals next_stage else true. 3 Set terminal true when current_stage is won or lost else false. 4 Decide valid: if not changed valid true; else if current_stage in OPEN valid true; else valid false (closed cannot leave to a different stage). 5 Set close true when changed and valid and next_stage is won or lost else false. 6 Set reason to noop when not changed, progress when valid open to open, close when valid open to closed, terminal_blocked when invalid closed to different. Returns dict with current_stage str, next_stage str, valid bool, changed bool, terminal bool, close bool, reason str. Raises ValueError on non-object payload, missing or bad stage types or unknown stage names. Caller must pre-filter deals to current account, map ValueError to user error and enforce ownership, map valid false to form error without saving; function does no ownership check, DB query, CSV handling or clock read and never mutates inputs. Guard only, not creation, update, deletion or permission enforcement. Application and UI integration is outside this change.

Examples (JSON input and expected output):

```json
{
  "input": {
    "current_stage": "new",
    "next_stage": "proposal"
  },
  "output": {
    "changed": true,
    "close": false,
    "current_stage": "new",
    "next_stage": "proposal",
    "reason": "progress",
    "terminal": false,
    "valid": true
  }
}
```

```json
{
  "input": {
    "current_stage": "qualified",
    "next_stage": "won"
  },
  "output": {
    "changed": true,
    "close": true,
    "current_stage": "qualified",
    "next_stage": "won",
    "reason": "close",
    "terminal": false,
    "valid": true
  }
}
```

```json
{
  "input": {
    "current_stage": "won",
    "next_stage": "lost"
  },
  "output": {
    "changed": true,
    "close": false,
    "current_stage": "won",
    "next_stage": "lost",
    "reason": "terminal_blocked",
    "terminal": true,
    "valid": false
  }
}
```

Public regression tests: `crm/test_community_deal_stage_transition_guard.py`.


<!-- community-core:deal-task-next-action -->
### Deal next open task map core

Lets the Portuguese self-hosted CRM spot opportunities without follow-up from pure JSON without database or clock reads. It maps each deal to its earliest open task and counts uncovered deals so callers share next-action ordering. Ownership filtering stays with the caller.

Reusable deterministic JSON core: `crm/features/deal_task_next_action.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) -> dict as a pure deterministic function with no I/O, env, time, randomness, callbacks or dependencies. Uses only plain functions and immutable literal module constants with local mutable containers. Input payload must be an object; extra keys ignored. Optional keys deals list default [] and tasks list default [] else ValueError; deals over 2000 or tasks over 5000 raises ValueError. Preserve inputs without mutation. Each deal must be an object with pk int excluding booleans at least 1 and title str else ValueError; extra keys ignored; raw title over 10000 raises ValueError; trimmed by stripping space TAB LF CR from both ends must be 1 to 180 else ValueError; duplicate deal pk raises ValueError. Each task must be an object with pk int excluding booleans at least 1 and title str and due_date str YYYY-MM-DD and completed bool and deal missing or None means unlinked else int excluding booleans at least 1 else ValueError; extra keys ignored; raw title over 10000 raises ValueError; trimmed title 1 to 180 else ValueError; duplicate task pk raises ValueError; due_date must be length 10 with dash at positions 4 and 7 and digits otherwise, year 0001 to 9999 month 01 to 12 day 01 to month length with February 29 only on leap years divisible by 4 except centuries unless divisible by 400 else ValueError. Steps: 1 Validate types bounds uniqueness and dates. 2 Count total_open_tasks as tasks with completed false. 3 For each deal in input order collect open tasks with deal equal to deal pk; null and unknown deal ids contribute only to total. 4 For each deal set open_count length and has_open true when count above 0 else false and next as minimal by due_date string ascending then pk ascending else null. 5 Build results in input deal order each with deal_pk deal_title trimmed has_open open_count next_pk next_title next_due_date with nulls when none. 6 Set total_deals as deals length and deals_with_open as count has_open true and deals_without_open as total minus with. Returns dict with total_deals deals_with_open deals_without_open total_open_tasks results. Raises ValueError on malformed types bounds titles dates or duplicates. Caller must pre-filter deals and tasks to current account, enforce ownership and map ValueError to user error; function does no ownership check, DB query, CSV handling or clock read and never mutates inputs. Coverage snapshot only, not creation update deletion or permission enforcement. Application and UI integration is outside this change.

Examples (JSON input and expected output):

```json
{
  "input": {
    "deals": [
      {
        "pk": 1,
        "title": "Padaria"
      },
      {
        "pk": 2,
        "title": "Mercado"
      }
    ],
    "tasks": [
      {
        "completed": false,
        "deal": 1,
        "due_date": "2026-03-10",
        "pk": 10,
        "title": "Ligar"
      },
      {
        "completed": false,
        "deal": 1,
        "due_date": "2026-03-08",
        "pk": 11,
        "title": "Visita"
      },
      {
        "completed": true,
        "deal": 2,
        "due_date": "2026-03-09",
        "pk": 12,
        "title": "Proposta"
      }
    ]
  },
  "output": {
    "deals_with_open": 1,
    "deals_without_open": 1,
    "results": [
      {
        "deal_pk": 1,
        "deal_title": "Padaria",
        "has_open": true,
        "next_due_date": "2026-03-08",
        "next_pk": 11,
        "next_title": "Visita",
        "open_count": 2
      },
      {
        "deal_pk": 2,
        "deal_title": "Mercado",
        "has_open": false,
        "next_due_date": null,
        "next_pk": null,
        "next_title": null,
        "open_count": 0
      }
    ],
    "total_deals": 2,
    "total_open_tasks": 2
  }
}
```

```json
{
  "input": {
    "deals": [
      {
        "pk": 5,
        "title": "Oficina"
      }
    ],
    "tasks": []
  },
  "output": {
    "deals_with_open": 0,
    "deals_without_open": 1,
    "results": [
      {
        "deal_pk": 5,
        "deal_title": "Oficina",
        "has_open": false,
        "next_due_date": null,
        "next_pk": null,
        "next_title": null,
        "open_count": 0
      }
    ],
    "total_deals": 1,
    "total_open_tasks": 0
  }
}
```

```json
{
  "input": {
    "deals": [
      {
        "pk": 1,
        "title": "A"
      },
      {
        "pk": 2,
        "title": "B"
      }
    ],
    "tasks": [
      {
        "completed": false,
        "deal": 1,
        "due_date": "2026-04-01",
        "pk": 20,
        "title": "Z "
      },
      {
        "completed": false,
        "deal": 1,
        "due_date": "2026-04-01",
        "pk": 19,
        "title": " Y "
      },
      {
        "completed": false,
        "deal": null,
        "due_date": "2026-04-02",
        "pk": 21,
        "title": "Livre"
      },
      {
        "completed": false,
        "deal": 99,
        "due_date": "2026-04-03",
        "pk": 22,
        "title": "Fantasma"
      },
      {
        "completed": true,
        "deal": 2,
        "due_date": "2026-04-05",
        "pk": 23,
        "title": "Fechada"
      }
    ]
  },
  "output": {
    "deals_with_open": 1,
    "deals_without_open": 1,
    "results": [
      {
        "deal_pk": 1,
        "deal_title": "A",
        "has_open": true,
        "next_due_date": "2026-04-01",
        "next_pk": 19,
        "next_title": "Y",
        "open_count": 2
      },
      {
        "deal_pk": 2,
        "deal_title": "B",
        "has_open": false,
        "next_due_date": null,
        "next_pk": null,
        "next_title": null,
        "open_count": 0
      }
    ],
    "total_deals": 2,
    "total_open_tasks": 4
  }
}
```

Public regression tests: `crm/test_community_deal_task_next_action.py`.


<!-- community-core:task-duplicate-finder -->
### Task duplicate finder core

Lets the Portuguese self-hosted CRM spot repeated follow-up tasks from pure JSON without database or clock reads. It groups tasks by normalized title plus due date plus linked deal so callers share duplicate warnings before creating extra follow-ups. Ownership filtering stays with the caller.

Reusable deterministic JSON core: `crm/features/task_duplicate_finder.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) -> dict as a pure deterministic function with no I/O, env, time, randomness, callbacks or dependencies. Uses only plain functions and immutable literal module constants with local mutable containers. Input payload must be an object; extra keys ignored. Optional key tasks list default [] else ValueError; length over 500 raises ValueError. Preserve inputs without mutation. Each task must be an object with pk int excluding booleans >=1, title str, due_date str YYYY-MM-DD valid calendar date including leap-year February, deal missing or None means null else int excluding booleans >=1, completed bool else ValueError; extra keys ignored; raw title over 10000 raises ValueError; duplicate task pk raises ValueError. Normalize title by stripping space TAB LF CR from both ends then casefold; normalized length 1..180 else ValueError. Validate due_date length 10 with dashes at positions 4 and 7 and digits otherwise, year 0001..9999 month 01..12 day 01.. month length with February 29 only on leap years divisible by 4 except centuries unless divisible by 400 else ValueError. Steps: 1 Validate types bounds uniqueness and dates. 2 Build key of normalized title plus due_date string plus deal null or int. 3 Group by key in first-seen order. 4 Keep only groups with count above 1 with task_pks sorted ascending; sort groups by due_date ascending then title_normalized ascending then deal null-first then int ascending. 5 Set total_tasks as tasks length and duplicate_group_count as kept groups length and duplicate_task_count as sum of kept counts. Returns dict with total_tasks, duplicate_group_count, duplicate_task_count, groups list each with title_normalized, due_date, deal, count, task_pks. Raises ValueError on malformed types bounds titles dates or duplicate pks. Caller must pre-filter tasks to current account, enforce ownership and map ValueError to user error; function does no ownership check, DB query, CSV handling or clock read and never mutates inputs. Duplicate snapshot only, not creation update deletion or permission enforcement. Application and UI integration is outside this change.

Examples (JSON input and expected output):

```json
{
  "input": {
    "tasks": [
      {
        "completed": false,
        "deal": 2,
        "due_date": "2026-03-10",
        "pk": 1,
        "title": " Retorno "
      },
      {
        "completed": false,
        "deal": 2,
        "due_date": "2026-03-10",
        "pk": 2,
        "title": "retorno"
      },
      {
        "completed": false,
        "deal": 2,
        "due_date": "2026-03-11",
        "pk": 3,
        "title": "Retorno"
      }
    ]
  },
  "output": {
    "duplicate_group_count": 1,
    "duplicate_task_count": 2,
    "groups": [
      {
        "count": 2,
        "deal": 2,
        "due_date": "2026-03-10",
        "task_pks": [
          1,
          2
        ],
        "title_normalized": "retorno"
      }
    ],
    "total_tasks": 3
  }
}
```

```json
{
  "input": {
    "tasks": [
      {
        "completed": false,
        "deal": null,
        "due_date": "2026-03-10",
        "pk": 1,
        "title": "Ligar"
      },
      {
        "completed": false,
        "deal": 5,
        "due_date": "2026-03-10",
        "pk": 2,
        "title": "Ligar"
      }
    ]
  },
  "output": {
    "duplicate_group_count": 0,
    "duplicate_task_count": 0,
    "groups": [],
    "total_tasks": 2
  }
}
```

Public regression tests: `crm/test_community_task_duplicate_finder.py`.


<!-- community-core:contact-draft-validator -->
### Contact draft validator core

Lets the Portuguese self-hosted CRM validate contact create and edit drafts from pure JSON without database or clock reads. It normalizes whitespace and reports required, length and format problems so forms and CSV flows share one hint. Ownership, company existence and duplicate email checks stay with the caller.

Reusable deterministic JSON core: `crm/features/contact_draft_validator.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) as a pure deterministic function with no IO, env, time, randomness, callbacks or dependencies. Uses only plain functions and immutable literal module constants with local mutable containers. Input payload must be an object; extra keys ignored. Optional keys name, email, phone, company, notes default to empty string when missing or None; present values must be str or None else ValueError; any str raw length over 10000 raises ValueError. Steps: 1 Validate types and bounds without mutation. 2 Normalize each field as raw or empty string stripped of space, TAB, LF and CR on both ends. 3 Validate normalized values: name length 1 to 180 else errors name required when empty else too_long; email empty allowed else if length over 254 errors email too_long else if not exactly one at-sign with non-empty local and domain, no space TAB LF CR, domain contains a dot not at ends, no double dot, suffix after last dot at least 2 chars else invalid; phone empty allowed else if length over 40 errors phone too_long else if chars other than digits, space, plus, minus, dot, slash and parentheses or no digit at all else invalid; company empty allowed else length 1 to 180 else too_long; notes length up to 2000 else too_long. 4 Build errors object with only failing fields each one of required, too_long or invalid and normalized object with five trimmed strings. Return dict with valid bool, errors object and normalized object. Raises ValueError on malformed payload or bounds. Preserves inputs without mutation. Caller must pre-filter to current account, verify company existence, enforce duplicate email policy and map ValueError to user error; function does no ownership check, DB query, CSV handling, file IO or clock read. Hint only, not creation, update, deletion or permission enforcement. Application and UI integration is outside this change.

Examples (JSON input and expected output):

```json
{
  "input": {
    "company": "Padaria Estrela",
    "email": "marina@example.com",
    "name": " Marina Silva ",
    "notes": "Fictional example",
    "phone": "+55 11 99999-0000"
  },
  "output": {
    "errors": {},
    "normalized": {
      "company": "Padaria Estrela",
      "email": "marina@example.com",
      "name": "Marina Silva",
      "notes": "Fictional example",
      "phone": "+55 11 99999-0000"
    },
    "valid": true
  }
}
```

```json
{
  "input": {
    "company": "",
    "email": "bad-email",
    "name": "   ",
    "notes": "",
    "phone": "abc"
  },
  "output": {
    "errors": {
      "email": "invalid",
      "name": "required",
      "phone": "invalid"
    },
    "normalized": {
      "company": "",
      "email": "bad-email",
      "name": "",
      "notes": "",
      "phone": "abc"
    },
    "valid": false
  }
}
```

```json
{
  "input": {},
  "output": {
    "errors": {
      "name": "required"
    },
    "normalized": {
      "company": "",
      "email": "",
      "name": "",
      "notes": "",
      "phone": ""
    },
    "valid": false
  }
}
```

Public regression tests: `crm/test_community_contact_draft_validator.py`.


<!-- community-core:task-deal-date-parser -->
### Task and deal date parser core

Offers Brazilian date entry for the Portuguese self-hosted CRM from pure JSON without database or clock reads, accepting DD/MM/YYYY alongside YYYY-MM-DD and normalizing to ISO for Task.due_date and Deal.expected_close storage with a Portuguese display form, so sellers type follow-up and forecast dates naturally while ownership filtering and persistence stay with the caller.

Reusable deterministic JSON core: `crm/features/task_deal_date_parser.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) -> dict as a pure deterministic function with no I/O, env, time, randomness, callbacks or dependencies. Uses only plain functions and immutable literal module constants with local mutable containers; no decorators/classes/async/generator/global/nonlocal, attribute assignment/deletion, dynamic calls or mutable defaults. Input payload must be an object (dict); extra keys ignored; None or non-dict raises ValueError. Key text is required str; missing/None/non-str raises ValueError. Raw text length over 5000 raises ValueError; normalized is text stripped of space TAB LF CR at both ends; empty normalized raises ValueError; normalized length over 100 raises ValueError. Accepted shapes only: ISO YYYY-MM-DD matching four digits dash two digits dash two digits, or BR D/M/YYYY matching one or two digits slash one or two digits slash four digits with no inner spaces; any mixed separators or other shape raises ValueError. Year must be 1 to 9999 else ValueError; month 1 to 12 else ValueError; day must be valid for month including Feb 29 on leap years where leap is divisible by 400 or divisible by 4 and not by 100 else ValueError. Steps: 1 Validate types and bounds without DB, clock or Date. 2 Strip to normalized. 3 Branch on slash presence to BR else ISO and parse integer parts without float. 4 Validate calendar range. 5 Build iso_date as YYYY-MM-DD zero-padded to 4/2/2 digits, year/month/day ints, input_format iso or br, display_br as DD/MM/YYYY zero-padded to 2/2/4 digits. Returns dict with iso_date str, year int, month int, day int, input_format str, display_br str. Raises ValueError on malformed types, bounds, shapes or calendar dates. Preserves inputs without mutation. Caller must enforce per-account ownership and map ValueError to user error; function does no ownership check, DB query, file I/O or clock read and never creates, merges, updates or deletes records. Normalized dates reflect supplied entry for Task.due_date and Deal.expected_close input, not delivery guarantee or permission enforcement. Application and UI integration is outside this change.

Examples (JSON input and expected output):

```json
{
  "input": {
    "text": "10/03/2026"
  },
  "output": {
    "day": 10,
    "display_br": "10/03/2026",
    "input_format": "br",
    "iso_date": "2026-03-10",
    "month": 3,
    "year": 2026
  }
}
```

```json
{
  "input": {
    "text": "2026-03-10"
  },
  "output": {
    "day": 10,
    "display_br": "10/03/2026",
    "input_format": "iso",
    "iso_date": "2026-03-10",
    "month": 3,
    "year": 2026
  }
}
```

```json
{
  "input": {
    "text": " 5/3/2026 "
  },
  "output": {
    "day": 5,
    "display_br": "05/03/2026",
    "input_format": "br",
    "iso_date": "2026-03-05",
    "month": 3,
    "year": 2026
  }
}
```

Public regression tests: `crm/test_community_task_deal_date_parser.py`.


<!-- community-core:contact-import-batch-guard -->
### Contact import batch limits guard core

Lets the Portuguese self-hosted CRM enforce documented contact CSV import ceilings from pure JSON without database or clock reads, so sellers fail closed before preview checks when a file exceeds 256 KiB or 500 rows or snapshots exceed 20000 contacts or companies while ownership and parsing stay with the caller.

Reusable deterministic JSON core: `crm/features/contact_import_batch_guard.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) -> dict as a pure deterministic function with no I/O, env, time, randomness, callbacks or dependencies. Uses only plain functions and immutable literal module constants with local mutable containers; no decorators/classes/async/generator/global/nonlocal, attribute assignment/deletion, dynamic calls or mutable defaults. Input payload must be an object (dict); extra keys ignored; None or non-dict raises ValueError. Required keys file_bytes, preview_rows, existing_contacts, matching_companies must be ints excluding booleans else ValueError; missing or None raises ValueError; negative raises ValueError. Limits are MAX_FILE_BYTES 262144, MAX_PREVIEW_ROWS 500, MAX_EXISTING_CONTACTS 20000, MAX_MATCHING_COMPANIES 20000. Steps: 1 Validate types and negativity without DB, clock or Date. 2 Start empty reasons list. 3 If file_bytes equals 0 append empty_file else if file_bytes exceeds MAX_FILE_BYTES append file_too_large. 4 If preview_rows equals 0 append empty_preview else if preview_rows exceeds MAX_PREVIEW_ROWS append too_many_rows. 5 If existing_contacts exceeds MAX_EXISTING_CONTACTS append too_many_existing_contacts. 6 If matching_companies exceeds MAX_MATCHING_COMPANIES append too_many_matching_companies. 7 Set allowed true when reasons empty else false. Returns dict with file_bytes, preview_rows, existing_contacts, matching_companies, allowed bool, reasons list, limits object with max_file_bytes, max_preview_rows, max_existing_contacts, max_matching_companies. Raises ValueError on malformed types or negativity. Preserves inputs without mutation. Caller must pre-filter counts to current account, enforce ownership, parse CSV and BOM, resolve exact company names, check duplicates, enforce 15-minute window with transactional replay protection and map ValueError to user error and allowed false to fail-closed block without creating contacts; function does no ownership check, DB query, file I/O, CSV parsing or clock read and never creates, merges, updates or deletes records. Limits reflect documented import ceilings, not delivery guarantee or permission enforcement. Application and UI integration is outside this change.

Examples (JSON input and expected output):

```json
{
  "input": {
    "existing_contacts": 10,
    "file_bytes": 1024,
    "matching_companies": 5,
    "preview_rows": 2
  },
  "output": {
    "allowed": true,
    "existing_contacts": 10,
    "file_bytes": 1024,
    "limits": {
      "max_existing_contacts": 20000,
      "max_file_bytes": 262144,
      "max_matching_companies": 20000,
      "max_preview_rows": 500
    },
    "matching_companies": 5,
    "preview_rows": 2,
    "reasons": []
  }
}
```

```json
{
  "input": {
    "existing_contacts": 0,
    "file_bytes": 262145,
    "matching_companies": 1,
    "preview_rows": 1
  },
  "output": {
    "allowed": false,
    "existing_contacts": 0,
    "file_bytes": 262145,
    "limits": {
      "max_existing_contacts": 20000,
      "max_file_bytes": 262144,
      "max_matching_companies": 20000,
      "max_preview_rows": 500
    },
    "matching_companies": 1,
    "preview_rows": 1,
    "reasons": [
      "file_too_large"
    ]
  }
}
```

```json
{
  "input": {
    "existing_contacts": 20001,
    "file_bytes": 100,
    "matching_companies": 20001,
    "preview_rows": 0
  },
  "output": {
    "allowed": false,
    "existing_contacts": 20001,
    "file_bytes": 100,
    "limits": {
      "max_existing_contacts": 20000,
      "max_file_bytes": 262144,
      "max_matching_companies": 20000,
      "max_preview_rows": 500
    },
    "matching_companies": 20001,
    "preview_rows": 0,
    "reasons": [
      "empty_preview",
      "too_many_existing_contacts",
      "too_many_matching_companies"
    ]
  }
}
```

Public regression tests: `crm/test_community_contact_import_batch_guard.py`.


<!-- community-core:company-website-link-guard -->
### Company website link guard core

Lets the Portuguese self-hosted CRM guard Company.website links from pure JSON without database, clock or network reads, so sellers keep blank websites allowed and render only http and https company links safely on server-rendered pages while javascript, data and other schemes plus missing hosts and unsafe characters block for review while ownership filtering, escaping, fetching and persistence stay with the caller.

Reusable deterministic JSON core: `crm/features/company_website_link_guard.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) -> dict as a pure deterministic function with no I/O, env, time, randomness, callbacks or dependencies. Uses only plain functions and immutable literal module constants with local mutable containers; no decorators, classes, async, generator, global, nonlocal, attribute assignment, deletion, dynamic calls or mutable defaults. Input payload must be an object (dict); extra keys ignored; None or non-dict raises ValueError. Optional key websites defaults to empty list when missing; None raises ValueError; non-list raises ValueError; length over 20 raises ValueError. Each website must be str else ValueError; raw length over 500 raises ValueError. Steps: 1 Validate types and bounds without DB, clock or network. 2 For each website in input order with index starting at 0, strip ASCII space, TAB, LF and CR at both ends to get trimmed. 3 If trimmed is empty, result kind blank with allowed true, href null, display_host empty string and empty reasons. 4 Else kind link; check scheme case-insensitive must start with http:// or https:// else blocked with reason unsafe_scheme; check trimmed must contain no space, TAB, LF or CR else reason contains_space; check trimmed must contain none of angle brackets, double quote word, single quote, backtick and backslash word else reason unsafe_chars; extract host as chars after scheme up to first slash, question or hash, else blocked with reason missing_host when empty; host must contain none of whitespace or angle or quote chars else blocked. 5 When all checks pass, allowed true, href trimmed, display_host lowercased host, reasons empty. 6 When any check fails, allowed false, href null, display_host empty string, reasons list with failing codes in fixed order unsafe_scheme, contains_space, unsafe_chars, missing_host. 7 Preserve input order and never mutate inputs. 8 Compute total_count, allowed_count and blocked_count. Returns dict with total_count int, allowed_count int, blocked_count int and results list each as index int, website original str, trimmed str, kind blank or link, allowed bool, href str or null, display_host str and reasons list. Raises ValueError on malformed types or bounds. Caller must pre-filter companies to current account, enforce ownership, escape href for anchor rendering, handle DB, file I/O and network fetching and map ValueError to user error; function does no ownership check, DB query, file I/O, network fetch, clock read and never creates, merges, updates or deletes records. Safe results reflect supplied snapshot syntax only, not reachability, delivery guarantee or permission enforcement. Application and UI integration is outside this change.

Examples (JSON input and expected output):

```json
{
  "input": {
    "websites": [
      "",
      "https://www.exemplo.com.br",
      "javascript:alert(1)"
    ]
  },
  "output": {
    "allowed_count": 2,
    "blocked_count": 1,
    "results": [
      {
        "allowed": true,
        "display_host": "",
        "href": null,
        "index": 0,
        "kind": "blank",
        "reasons": [],
        "trimmed": "",
        "website": ""
      },
      {
        "allowed": true,
        "display_host": "www.exemplo.com.br",
        "href": "https://www.exemplo.com.br",
        "index": 1,
        "kind": "link",
        "reasons": [],
        "trimmed": "https://www.exemplo.com.br",
        "website": "https://www.exemplo.com.br"
      },
      {
        "allowed": false,
        "display_host": "",
        "href": null,
        "index": 2,
        "kind": "link",
        "reasons": [
          "unsafe_scheme"
        ],
        "trimmed": "javascript:alert(1)",
        "website": "javascript:alert(1)"
      }
    ],
    "total_count": 3
  }
}
```

```json
{
  "input": {
    "websites": [
      "  https://Loja.Exemplo.com/caminho  ",
      "https://exemplo.com/a<b",
      "https://"
    ]
  },
  "output": {
    "allowed_count": 1,
    "blocked_count": 2,
    "results": [
      {
        "allowed": true,
        "display_host": "loja.exemplo.com",
        "href": "https://Loja.Exemplo.com/caminho",
        "index": 0,
        "kind": "link",
        "reasons": [],
        "trimmed": "https://Loja.Exemplo.com/caminho",
        "website": "  https://Loja.Exemplo.com/caminho  "
      },
      {
        "allowed": false,
        "display_host": "",
        "href": null,
        "index": 1,
        "kind": "link",
        "reasons": [
          "unsafe_chars"
        ],
        "trimmed": "https://exemplo.com/a<b",
        "website": "https://exemplo.com/a<b"
      },
      {
        "allowed": false,
        "display_host": "",
        "href": null,
        "index": 2,
        "kind": "link",
        "reasons": [
          "missing_host"
        ],
        "trimmed": "https://",
        "website": "https://"
      }
    ],
    "total_count": 3
  }
}
```

```json
{
  "input": {},
  "output": {
    "allowed_count": 0,
    "blocked_count": 0,
    "results": [],
    "total_count": 0
  }
}
```

Public regression tests: `crm/test_community_company_website_link_guard.py`.


<!-- community-core:contact-import-confirm-gate -->
### Contact import confirm gate core

Lets the Portuguese self-hosted CRM decide an explicit contact CSV confirmation from pure JSON without database or clock reads, mirroring all-or-nothing confirmation with durable replay receipt and canonical preview state so sellers keep second confirmations blocked, old previews after re-upload rejected, invalid replacements held not ready, expired previews blocked and missing session CSV failed closed for re-upload while ownership filtering, expiry timing, CSV storage and transactional saving stay with the caller.

Reusable deterministic JSON core: `crm/features/contact_import_confirm_gate.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) as a pure deterministic function with no I/O, env, time, randomness, callbacks or dependencies. Uses only plain functions and immutable literal module constants with local mutable containers; no decorators, classes, async, generator, global, nonlocal, attribute assignment, deletion, dynamic calls or mutable defaults. Input payload must be an object; extra keys ignored; None or non-dict raises ValueError. Required keys presented_nonce_digest, canonical_nonce_digest, presented_session_digest, canonical_session_digest each must be str of length 64 with only 0-9 and a-f else ValueError; required keys canonical_ready, canonical_expired, receipt_exists, session_has_csv each must be bool exactly else ValueError; missing keys raise ValueError. Caller supplies digests and flags pre-filtered to the current account from stored receipt, canonical preview and session presence and computes expiry from its own clock; function does no ownership check, DB query, file I/O, session read or clock read and never mutates inputs. Steps: 1 Validate types and hex shape without DB or clock. 2 If session_has_csv is False return decision reupload. 3 Else if presented_session_digest differs from canonical_session_digest return session_mismatch. 4 Else if presented_nonce_digest differs from canonical_nonce_digest return stale_preview. 5 Else if canonical_expired is True return expired. 6 Else if canonical_ready is False return not_ready. 7 Else if receipt_exists is True return replayed. 8 Else return allow. Returns dict with decision str one of allow, reupload, session_mismatch, stale_preview, expired, not_ready, replayed and can_import bool true only when decision is allow else false. Raises ValueError on malformed types or shapes. Caller must pre-filter digests to current account, enforce ownership, load canonical preview and receipt records, track session CSV presence, enforce the 15-minute window via canonical_expired, handle CSV bytes, transactions and retries and map ValueError to user error; function creates, merges, updates or deletes no records. Decisions reflect supplied snapshot only, not history, delivery guarantee or permission enforcement. Application and UI integration is outside this change.

Examples (JSON input and expected output):

```json
{
  "input": {
    "canonical_expired": false,
    "canonical_nonce_digest": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "canonical_ready": true,
    "canonical_session_digest": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
    "presented_nonce_digest": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "presented_session_digest": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
    "receipt_exists": false,
    "session_has_csv": true
  },
  "output": {
    "can_import": true,
    "decision": "allow"
  }
}
```

```json
{
  "input": {
    "canonical_expired": false,
    "canonical_nonce_digest": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "canonical_ready": true,
    "canonical_session_digest": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
    "presented_nonce_digest": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "presented_session_digest": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
    "receipt_exists": true,
    "session_has_csv": true
  },
  "output": {
    "can_import": false,
    "decision": "replayed"
  }
}
```

```json
{
  "input": {
    "canonical_expired": false,
    "canonical_nonce_digest": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "canonical_ready": true,
    "canonical_session_digest": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
    "presented_nonce_digest": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "presented_session_digest": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
    "receipt_exists": false,
    "session_has_csv": true
  },
  "output": {
    "can_import": false,
    "decision": "stale_preview"
  }
}
```

Public regression tests: `crm/test_community_contact_import_confirm_gate.py`.


<!-- community-core:list-filter-state-keeper -->
### Filter-preserving list state core

Lets the Portuguese self-hosted CRM keep documented list filters while paging from pure JSON without database or clock reads, mirroring contacts q.strip()[:200] with keep-only-page-plus-q URLs and tasks status fallback to all with q combining, so sellers retain search and status context across pages while ownership filtering, record matching, pagination slicing and URL encoding stay with the caller.

Reusable deterministic JSON core: `crm/features/list_filter_state_keeper.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) -> dict as a pure deterministic function with no I/O, env, time, randomness, callbacks or dependencies. Uses only plain functions and immutable literal module constants with local mutable containers; no decorators, classes, async, generator, global, nonlocal, attribute assignment, deletion, dynamic calls or mutable defaults. Input payload must be an object (dict); extra keys ignored; None or non-dict raises ValueError. Required key view must be str one of contacts, tasks else ValueError; missing raises ValueError. Optional key q defaults to empty string when missing or None; non-str raises ValueError; str normalized as q.strip()[:200]. Optional key status handling per view: for contacts input ignored of any type with output None; for tasks missing/None/empty-string means all, otherwise must be str else ValueError with known values open, overdue, today, upcoming, completed, all kept and any other string falling back to all without raising. Steps: 1 Validate types without DB, clock or Date. 2 Normalize q. 3 Canonicalize status per view. 4 Build preserved object with only non-default filters: for contacts include q only when non-empty; for tasks include q only when non-empty and status only when not all. 5 Set total_preserved to preserved length. Returns dict with view str echo, q str normalized, status str for tasks or None for contacts, preserved object, total_preserved int. Raises ValueError on malformed types or missing view. Preserves inputs without mutation. Caller must pre-filter records to current account, enforce ownership, implement q/status record matching, paginate via Paginator.get_page, encode URLs, handle TIME_ZONE dating and map ValueError to user error; function does no ownership check, DB query, file I/O, CSV handling, clock read, record creation, merge, update or delete and never mutates inputs. Filter state reflects supplied query only, not history, realized revenue, conversion or future guarantee. Application and UI integration is outside this change.

Examples (JSON input and expected output):

```json
{
  "input": {
    "q": "  Marina  ",
    "view": "contacts"
  },
  "output": {
    "preserved": {
      "q": "Marina"
    },
    "q": "Marina",
    "status": null,
    "total_preserved": 1,
    "view": "contacts"
  }
}
```

```json
{
  "input": {
    "q": " retorno ",
    "status": "bogus",
    "view": "tasks"
  },
  "output": {
    "preserved": {
      "q": "retorno"
    },
    "q": "retorno",
    "status": "all",
    "total_preserved": 1,
    "view": "tasks"
  }
}
```

Public regression tests: `crm/test_community_list_filter_state_keeper.py`.


<!-- community-core:local-asset-guard -->
### Local frontend asset guard core

Lets the Portuguese self-hosted CRM verify server-rendered pages keep the documented no-external-frontend-CDN promise from pure JSON without database, clock, network or file reads, classifying supplied href/src strings as local or external so maintainers catch CDN drift before serving pages while ownership filtering, template rendering, URL fetching and offline checks stay with the caller.

Reusable deterministic JSON core: `crm/features/local_asset_guard.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) -> dict as a pure deterministic function with no I/O, env, time, randomness, callbacks or dependencies. Uses only plain functions and immutable literal module constants with local mutable containers; no decorators, classes, async, generator, global, nonlocal, attribute assignment, deletion, dynamic calls or mutable defaults. Input payload must be an object (dict); extra keys ignored; None or non-dict raises ValueError. Optional key assets defaults to [] when missing; None raises ValueError; non-list raises ValueError; length over 50 raises ValueError. Each asset must be str else ValueError; length 1 to 1000 else ValueError; blank after strip (asset.strip()=='') raises ValueError. Steps: 1 Validate types and bounds without DB, clock, network or file read. 2 Trim each asset with strip to trimmed preserving inner case. 3 Classify as external when trimmed.casefold() starts with 'http://', 'https://' or '//', else local; data:, blob:, relative, root-absolute and same-origin paths are local. 4 Build external and local lists of trimmed strings in input order including duplicates. 5 Count total, external_count, local_count and set allows_offline True only when external_count==0. Returns dict with total int, external_count int, local_count int, allows_offline bool, external list, local list. Raises ValueError on malformed types, bounds or blank assets. Preserves inputs without mutation. Caller must pre-extract href/src strings to current page, enforce ownership, handle rendering, encoding, file I/O, network fetch and clock and map ValueError to user error; function does no ownership check, DB query, file I/O, network fetch, clock read, record creation, merge, update or delete and never mutates inputs. Result reflects supplied list only, not history, delivery guarantee or permission enforcement. Application and UI integration is outside this change.

Examples (JSON input and expected output):

```json
{
  "input": {
    "assets": [
      "/static/crm/app.css",
      "https://cdn.example.com/lib.js"
    ]
  },
  "output": {
    "allows_offline": false,
    "external": [
      "https://cdn.example.com/lib.js"
    ],
    "external_count": 1,
    "local": [
      "/static/crm/app.css"
    ],
    "local_count": 1,
    "total": 2
  }
}
```

```json
{
  "input": {},
  "output": {
    "allows_offline": true,
    "external": [],
    "external_count": 0,
    "local": [],
    "local_count": 0,
    "total": 0
  }
}
```

```json
{
  "input": {
    "assets": [
      "//cdn.example.com/x.js",
      "  HTTP://example.com/y.js ",
      "/static/crm/app.css",
      "data:text/css,body{}"
    ]
  },
  "output": {
    "allows_offline": false,
    "external": [
      "//cdn.example.com/x.js",
      "HTTP://example.com/y.js"
    ],
    "external_count": 2,
    "local": [
      "/static/crm/app.css",
      "data:text/css,body{}"
    ],
    "local_count": 2,
    "total": 4
  }
}
```

Public regression tests: `crm/test_community_local_asset_guard.py`.


<!-- community-core:cross-record-owner-match -->
### Cross-record owner match core

Lets the Portuguese self-hosted CRM verify Contact.company, Deal.company/contact and Task.deal links stay inside one account from pure JSON without database reads, mirroring OwnedRecord.validate_related_owners, so sellers see Escolha um registro da sua conta before saving while fetching and saving stay with the caller.

Reusable deterministic JSON core: `crm/features/cross_record_owner_match.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) -> dict as a pure deterministic function with no I/O, env, time, randomness, callbacks or dependencies. Uses only plain functions and immutable literal module constants with local mutable containers; no decorators, classes, async, generator, global, nonlocal, attribute assignment, deletion, dynamic calls or mutable defaults. Input payload must be an object (dict); extra keys ignored; None or non-dict raises ValueError. Required key owner_id must be int exactly (booleans rejected) >=1 else ValueError; missing raises ValueError. Optional key links defaults to [] when missing; None raises ValueError; non-list raises ValueError; length over 10 raises ValueError. Each link must be dict else ValueError; extra keys ignored. Each link requires field str one of company, contact, deal else ValueError; missing raises ValueError. Duplicate field values in one payload raise ValueError. Optional link key related_owner_id defaults to None when missing; None allowed; otherwise must be int exactly (booleans rejected) >=1 else ValueError. Steps: 1 Validate types without DB, clock or Date. 2 For each link where related_owner_id is not None and not equal to owner_id add errors entry field to Portuguese message Escolha um registro da sua conta. 3 Set valid True when errors empty else False. 4 Set checked to links length and violated to errors length. Returns dict with owner_id int echo, checked int, violated int, valid bool, errors object mapping violating field to message. Raises ValueError on malformed types, unknown fields or duplicate fields. Preserves inputs without mutation. Caller must pre-resolve owner and related owner ids to current account records, enforce record ownership, implement fetching, validation scope and saving and map ValueError to user error; function does no ownership lookup, DB query, file I/O, CSV handling, clock read, record creation, merge, update or delete and never mutates inputs. Link result reflects supplied ids only under SET_NULL semantics where None links always pass; not history, realized revenue, conversion or future guarantee. Application and UI integration is outside this change.

Examples (JSON input and expected output):

```json
{
  "input": {
    "links": [
      {
        "field": "company",
        "related_owner_id": 7
      },
      {
        "field": "contact",
        "related_owner_id": null
      }
    ],
    "owner_id": 7
  },
  "output": {
    "checked": 2,
    "errors": {},
    "owner_id": 7,
    "valid": true,
    "violated": 0
  }
}
```

```json
{
  "input": {
    "links": [
      {
        "field": "deal",
        "related_owner_id": 9
      }
    ],
    "owner_id": 7
  },
  "output": {
    "checked": 1,
    "errors": {
      "deal": "Escolha um registro da sua conta."
    },
    "owner_id": 7,
    "valid": false,
    "violated": 1
  }
}
```

```json
{
  "input": {
    "owner_id": 5
  },
  "output": {
    "checked": 0,
    "errors": {},
    "owner_id": 5,
    "valid": true,
    "violated": 0
  }
}
```

Public regression tests: `crm/test_community_cross_record_owner_match.py`.
