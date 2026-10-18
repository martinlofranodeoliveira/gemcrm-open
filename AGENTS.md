# Working on GemCRM Open

This is a new, independent MIT-licensed CRM. Use only this repository and
public, appropriately licensed references. Never read or copy adjacent private
projects, customer records, local credentials, or machine-specific configuration.

Ship complete, useful changes. One feature or bug fix belongs in one meaningful
commit, including the necessary tests and documentation. Never split or invent
changes to increase contribution counts. Do not make empty commits.

Preserve per-user ownership filtering on every query, object lookup, foreign-key
choice, and export. A new endpoint needs ownership regression tests. Mutations
must use POST with CSRF protection. Treat exported spreadsheet cells as untrusted.

Run `uv run python manage.py check`, `uv run python manage.py makemigrations --check`
and `uv run python manage.py test` before proposing a change. Do not publish local
databases, .env files, demo credentials or generated logs. Dependency, authentication,
deployment, license and automation changes need maintainer review.

Use ROADMAP.md for real work. An exhausted backlog means inspect useful defects
or await the next task; it never authorizes synthetic activity.
