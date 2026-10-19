# Contact CSV import

The importer extends the existing Contacts workspace and [DESIGN.md](../../DESIGN.md): teal navigation, emerald actions, system typography, bordered surfaces and native controls.

## Workflow

Open **Contatos → Importar CSV**. Files must be UTF-8 (BOM allowed), comma separated,
at most 256 KiB and 500 contacts. The header requires `name`; `email`, `phone`, `company` and `notes` are optional. Quote values containing commas.
Companies must already match one unambiguous exact name in the current account. Repeated emails block the batch; blank emails are allowed. See the [README](../../README.md#import-contacts-from-csv)
for matching rules and maintenance.

| State | Feedback and next action |
| --- | --- |
| Choose file | Instructions and native file field; **Revisar arquivo** starts review |
| Ready | Preview, count and “Nenhum contato foi salvo”; **Importar … contatos** follows the table |
| Needs changes | Line errors and duplicate labels; correct and upload again, without confirmation |
| Confirmation failed | Explanation of expiry, reuse, changed records or failed save; follow the recovery message |
| Imported | Contacts list with the number created |

One action is primary per stage; another upload becomes secondary when confirmation
is available. Every upload invalidates the prior preview, including invalid replacements.
**Voltar sem importar** creates no contacts. Existing contacts are never merged or updated.

## Layout and accessibility

Upload and guidance stack at 1000px and below; the mobile shell applies at 700px.
The semantic table retains headers, row numbers and a screen-reader caption inside a named, focusable scroll region (`tabindex="0"`). Sticky headers support long batches.
The region's `position: relative` contains absolutely positioned screen-reader-only text and preserves document width. Long errors have a labeled, focusable scroll region.
Native `details` reveal observations with row/name context in each accessible summary,
and reveal the fictitious CSV example. Labels, help text, visible focus, alerts and
explicit status text support keyboard operation and avoid color-only feedback.

## State and privacy

Preview creates no contacts. Valid CSV stays in a database-backed server session;
confirmation sends a token, without contact rows. Signed-cookie sessions are rejected.
Account/session-bound state invalidates replaced previews; durable receipts prevent replay. Confirmation revalidates records and saves the batch and receipt in one transaction.
SQLite contention may require retry; manual editing gains no global email uniqueness constraint.

The **15-minute confirmation window is not a deletion timer**. Drafts follow session
retention unless replaced, consumed or logged out. Treat session storage and backups
as private contact data. Expired import-state/receipt cleanup does not remove CSV
from an unexpired session or delete contacts.

## Verification and limits

Change validation reported **106 passing tests: 74 public repository tests and
32 independent regression checks**. Reproduce the public checks with:

```sh
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run python manage.py test
```

Four captures covered synthetic valid/error previews at desktop (1440×1000) and mobile
(390×844) browser viewports. A browser check imported three synthetic contacts. Finish
review found no material visual issue in scope. This experimental SQLite baseline
makes no production-readiness or certified contrast claim. Implementation:
[template](../../templates/crm/contact_import.html), [styles](../../static/crm/app.css), [workflow](../../crm/contact_import_workflow.py).
