---
description: Python naming, typing, imports, file organization, and tooling rules for the FastAPI server.
---

# Python Code Conventions Rules

These rules apply to Python under `apps/server/src` and `apps/server/tests`.

## Use the project toolchain

Run Python commands from `apps/server` through `uv`. The server targets Python 3.13
and uses Ruff for linting and formatting, Pyright in strict mode for static typing,
and pytest for tests. Do not install project dependencies into a global interpreter.

Exact commands belong in `apps/server/pyproject.toml`; documentation and CI must call
those project commands instead of maintaining parallel flag lists.

## Follow Python naming consistently

- modules and functions use `snake_case`;
- classes and protocols use `PascalCase`;
- constants use `UPPER_SNAKE_CASE`;
- private implementation details start with `_`;
- use-case classes end in `UseCase`;
- repository protocols use plural resource names ending in `Repository`;
- concrete SQLAlchemy repositories start with `Sqlalchemy`;
- provider implementations name the technology and capability, such as
  `Argon2idHashProvider`;
- controllers, routers, pipes, jobs, models, mappers, and fakers end with the matching
  role name.

Use one primary public class per module and name the file after it in `snake_case`.
Small private dataclasses or helpers used only by that class may remain in the same
module.

## Type all boundaries

Type every public function, method, constructor argument, and return value. Prefer
Python 3.13 syntax:

```python
def find_by_id(account_id: Id) -> Account | None: ...

def add_many(accounts: list[Account]) -> None: ...
```

Use built-in generic collections and `X | None`; do not introduce legacy `List`,
`Dict`, or `Optional` forms. Import collection protocols such as `Iterator`,
`Callable`, and `Awaitable` from `collections.abc`.

Avoid `Any`. When an untyped external SDK makes it unavoidable, contain it inside the
adapter and add the narrowest local cast or targeted Pyright suppression with a reason.
Never weaken project-wide strictness to accommodate one dependency.

## Use absolute first-party imports

Imports across server modules use the installed package path:

```python
from shifu.learning.core.interfaces import AttemptsRepository
```

Do not use parent-relative imports between layers. Relative imports are allowed only
inside an `__init__.py` that re-exports neighboring declarations.

Order imports as standard library, third-party packages, then `shifu` imports. Use
`TYPE_CHECKING` for imports required only by static analysis and local imports only to
break a proven import cycle or defer an expensive optional adapter.

## Keep package exports explicit

An `__init__.py` may re-export the small public surface of its package. It must define
`__all__` when it re-exports names and must not perform registration, I/O, environment
loading, or other side effects.

Consumers may import from a package barrel when the declaration is intentionally
public. Internal declarations should be imported from their defining module.

## Keep functions focused

Use early returns for missing or terminal states. Prefer guard clauses over deeply
nested branches. Do not hide business logic in decorators, framework callbacks,
properties, or generic utility modules.

Use `async def` only when the implementation awaits non-blocking work. Synchronous
SQLAlchemy sessions and blocking SDK calls must not run directly on the event loop;
keep the endpoint synchronous or move the blocking operation to a worker thread.

## Treat environment access as infrastructure

Load and validate environment values once through the server environment settings
boundary. Core entities and use cases must not read `os.environ`, `.env`, or framework
settings directly. Tests override the settings boundary with pytest fixtures or
`monkeypatch` and restore state after the scenario.

Never log credentials, tokens, raw authorization headers, model prompts containing
private user data, or sandbox secrets.

## Tool suppressions stay local

Do not add broad Ruff `noqa`, Pyright ignores, or pytest warning filters. Place a
suppression on the exact expression that requires it and name the diagnostic whenever
the tool supports that. Delete obsolete suppressions during nearby refactors.

