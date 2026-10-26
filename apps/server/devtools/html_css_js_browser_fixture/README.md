# SHIFU-86 browser fixture

This helper prepares a mixed HTML/CSS/JavaScript activity for authenticated
browser validation. The repository seed clears application tables, so the
helper requires an explicit disposable-database acknowledgement. It only
accepts the loopback PostgreSQL database `shifu` on port `15448`, separate from
the Compose database on port `54344`.

Start a disposable PostgreSQL 17 instance on `127.0.0.1:15448`. Then, from
`apps/server`, set the fixture-only URL and acknowledgement and run:

```powershell
$env:SHIFU_HTML_FIXTURE_DATABASE_URL = 'postgresql+psycopg://shifu:shifu-local@127.0.0.1:15448/shifu'
$env:SHIFU_HTML_FIXTURE_DISPOSABLE = '1'
.venv/Scripts/python.exe devtools/html_css_js_browser_fixture/prepare.py
```

Use the same URL for the dedicated API and the database portion of
`BETTER_AUTH_DATABASE_URL`. Point the dedicated Web process at that API. The
seeded account is `student.seed@shifu.com`; its local password is defined by
`SEED_ACCOUNT_PASSWORD` in `src/shifu/shared/database/seed_data.py`. The fixture
adds “Prática HTML: lista de tarefas” to the seeded Logic Programming sequence.
It does not start or stop Docker, API, or Web processes and never prints the
database URL.
