# SHIFU-88 browser fixture

`prepare.py` upgrades and seeds a PostgreSQL database explicitly designated as
disposable, then adds a mixed activity to the seeded Logic Programming
competency. The repository seed clears all application tables, so this helper
requires an explicit URL and acknowledgement. It refuses the Compose/default
ports `5432` and `54344`, non-loopback hosts, and database names other than
`shifu`.

From `apps/server`, with the disposable PostgreSQL service already running, set
the fixture-only URL in the shell and run:

```powershell
$env:SHIFU_REACT_FIXTURE_DATABASE_URL = 'postgresql+psycopg://shifu:<password>@127.0.0.1:15448/shifu'
$env:SHIFU_REACT_FIXTURE_DISPOSABLE = '1'
.venv/Scripts/python.exe devtools/react_browser_fixture/prepare.py
```

Use the same URL as `DATABASE_URL` for the dedicated API. Start the dedicated
Web process with `VITE_SHIFU_SERVER_URL` and `SHIFU_IDENTITY_API_URL` pointing at
that API, and set `BETTER_AUTH_DATABASE_URL` to the same database so the browser
session stays in the disposable fixture. The helper itself does not start or
stop Docker, API, or Web services, and it does not display the database URL.

The seeded account is `student.seed@shifu.com`; its local development password
is defined by `SEED_ACCOUNT_PASSWORD` in
`src/shifu/shared/database/seed_data.py`. The inserted activity is titled
“Prática React: estado e contador” and has two choice questions plus one React
question. It is appended to the existing competency sequence under the seeded
goal and skill.
