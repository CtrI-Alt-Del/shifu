---
description: Pytest unit-testing rules for Python core use cases and domain fakers.
---

# Use Case Testing Rules

These rules apply to unit tests under `apps/server/tests/core`. Only use cases receive
dedicated unit tests, placed under `apps/server/tests/core/<module>/use_cases`.

Do not create dedicated unit tests for domain entities, structures, enums, errors,
events, decorators, interfaces, repositories, providers, fakers, or adapters. Exercise
those declarations through the use cases that consume them; use strict static typing,
architecture checks, and adapter-level integration tests for their other boundaries.

## One test module per use case

Mirror the production module name:

```text
src/shifu/learning/core/use_cases/submit_activity_use_case.py
tests/core/learning/use_cases/test_submit_activity_use_case.py
```

Group scenarios in `TestSubmitActivityUseCase`. Test names start with `test_should_`
and state the observable behavior and relevant condition.

## Use-case tests are infrastructure-free

Instantiate the use case directly. Do not create a FastAPI app, send HTTP requests,
open a SQLAlchemy session, start Docker, invoke Inngest, or instantiate production
providers.

Mock every repository and provider port with `unittest.mock.create_autospec` using the
`Protocol` as the specification:

```python
self.attempts_repository = create_autospec(
    AttemptsRepository,
    instance=True,
)
```

Prefer an `autouse=True` pytest fixture on the test class to create fresh mocks and the
subject for each scenario. Do not use loose dictionaries or handwritten objects when a
typed port exists.

## Cover behavior and collaboration

Every use case test module covers, as applicable:

- successful output and resulting domain state;
- repository writes and important provider calls;
- validation and normalization failures;
- not-found, forbidden, conflict, and invalid-transition cases;
- event publication and complete event payloads;
- idempotency or concurrency guards;
- absence of side effects after rejection.

Assert meaningful returned values and dependency calls. Avoid assertions tied only to
private implementation order when order is not part of the contract.

For failure paths, use `pytest.raises` with the exact domain error and assert that
downstream dependencies were not called.

## Time and identifiers are deterministic

Use cases that need the current time, random values, IDs, tokens, or model selection
receive those capabilities through core ports. Tests configure deterministic return
values. Do not patch the Python clock or rely on real randomness when an injected port
owns that capability.

## Use domain fakers selectively

Use the shared domain faker when a valid entity or structure has many fields. Override
only the fields relevant to the scenario. Small request primitives may remain inline.

Do not create provider fakers. Provider and repository dependencies are autospecced
mocks; fakers are reserved for domain data.

## Keep tests independent

Mocks, mutable DTOs, lists, and entities are recreated for every test. Tests must not
depend on execution order or leak configured return values to another scenario.

Run focused tests through `uv run pytest <path>` from `apps/server`. Before delivery,
run the complete core test selection plus Ruff and strict type checking configured by
the server project.
