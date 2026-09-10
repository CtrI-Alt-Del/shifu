
# Shifu API

FastAPI application for Shifu. The server is organized by business module so
each module owns its domain, persistence adapters, REST boundary, asynchronous
messaging, and external providers.

```text
src/shifu/
├── identity/
├── curriculum/
├── learning/
├── gamification/
├── intelligence/
├── composition/
├── shared/
└── app.py
```

Each business module follows this shape:

```text
<module>/
├── core/
│   ├── domain/
│   │   ├── entities/
│   │   ├── structures/
│   │   ├── errors/
│   │   └── events/
│   ├── interfaces/
│   └── use_cases/
├── database/sqlalchemy/
│   ├── models/
│   ├── mappers/
│   └── repositories/
├── rest/
│   ├── controllers/
│   ├── schemas/
│   └── router.py
├── messaging/
│   ├── brokers/
│   └── jobs/
└── providers/
```

`composition` is the application assembly point. `shared` contains only
cross-module infrastructure. Transport schemas are created at REST boundaries;
there are no DTO directories for individual domain objects.

Run the API locally from this directory:

```bash
uv run uvicorn main:app --app-dir src --reload
```
