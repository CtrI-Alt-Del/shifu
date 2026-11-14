# Structured telemetry

Shifu's Web/BFF and API operational output is one JSON object per line. The
provider is best effort: telemetry serialization or emission failures never
change the result of the operation being observed.

## Common event shape

Every accepted event contains:

| Field | Contract |
| --- | --- |
| `timestamp` | RFC3339 UTC string with a `Z` suffix |
| `level` | `DEBUG`, `INFO`, `WARNING` or `ERROR`, filtered by the configured threshold |
| `service` | `shifu-web` or `shifu-api` |
| `environment` | `dev`, `local`, `staging` or `production` |
| `version` | configured release version |
| `event` | fixed catalog event name |
| `message` | fixed message derived from the event catalog |

Optional technical fields are limited to `request_id`, `run_id`, `event_id`,
`method`, resolved route template, integer `status_code`, finite non-negative
`duration_ms`, cataloged `operation`, `job`, `integration`, `dependency`,
`result`, positive `attempt`, `error_code`, `exception_type` and sanitized
`stack_trace` frames. Request IDs are UUID v4 values. Run and event IDs are
opaque ASCII values of at most 128 characters and are never derived from event
payload content.

Unknown fields and invalid optional catalog values are omitted. Required
catalog values are validated at the typed boundary and rejected defensively at
runtime. Caller-supplied `timestamp`, `service`, `environment`, `version` and
`message` values are ignored.

## Event catalog

| Event | Fixed message |
| --- | --- |
| `http.request.completed` / `http.request.failed` | HTTP request completed / HTTP request failed |
| `error.unexpected` | Unexpected error |
| `auth.login.succeeded` / `auth.login.refused` | Authentication succeeded / Authentication refused |
| `auth.session.revoked` / `auth.access.denied` | Session revoked / Access denied |
| `learning.goal.created` / `learning.goal.deleted` | Learning goal created / Learning goal deleted |
| `learning.attempt.submitted` / `learning.evaluation.completed` | Learning attempt submitted / Learning evaluation completed |
| `job.started` / `job.completed` / `job.failed` / `job.retrying` | Job started / Job completed / Job failed / Job retrying |
| `integration.operation.started` / `integration.operation.completed` | Integration operation started / Integration operation completed |
| `integration.operation.failed` / `integration.operation.retrying` | Integration operation failed / Integration operation retrying |
| `app.startup.completed` / `app.shutdown.completed` | Application startup completed / Application shutdown completed |
| `app.version.reported` / `dependency.unavailable` | Application version reported / Dependency unavailable |

The `job` catalog contains the stable `<module>.<job_name>` identifiers for
the 15 registered Inngest jobs. `operation` values are `http.request`,
`auth.login`, `auth.session.revoke`, `auth.access`, `goal.create`,
`goal.delete`, `attempt.submit`, `evaluation.complete`, `app.startup`,
`app.shutdown`, `dependency.check`, `inngest.dispatch`, `resend.send` and
`openrouter.generate`.

## Privacy boundary

Telemetry must not contain passwords, tokens, cookies, secrets, raw
authorization headers, request bodies, account/user/attempt/goal/activity
identifiers, IP addresses, user agents, Mentor conversations, submitted code,
email contents, provider prompts/responses or raw exception messages. Error
events retain only a stable catalog code, exception type and at most 20
basename-only stack frames with optional positive line and function values.

Business events are emitted by the owning Identity or Learning boundary after
its terminal outcome. Authorization denial is emitted by the shared error
boundary. A retry dispatch does not emit evaluation completion; the completed
evaluation job owns that event.

## Configuration

Web reads server-only `SHIFU_WEB_APP_MODE`, `SHIFU_WEB_APP_LOG_LEVEL` and
`SHIFU_RELEASE_VERSION`. API reads `SHIFU_SERVER_APP_MODE`,
`SHIFU_SERVER_LOG_LEVEL` and `SHIFU_RELEASE_VERSION`. Modes are `dev`, `local`,
`staging` and `production`; log levels default to `INFO`. `DEBUG` is enabled
only by deployment configuration. `SHIFU_RELEASE_VERSION` defaults to
`local-dev` in `dev`/`local` and is required in `staging`/`production`.

## Correlation

At each HTTP boundary, a valid inbound UUID v4 `X-Request-ID` is retained;
missing or invalid values are replaced. The response echoes the bounded ID,
and the Web/BFF forwards it to API requests made by server functions. Routes
are resolved templates or `unmatched`, never raw request paths. Jobs and
integrations use SDK-provided opaque `run_id`/`event_id` values when available.

## CloudWatch examples

The JSON lines can be queried in CloudWatch Logs Insights without sending
payload data to the log stream:

```text
fields @timestamp, service, environment, version, event, level, request_id, run_id, event_id, duration_ms
| filter service = "shifu-api"
| sort @timestamp desc
| limit 100
```

```text
fields @timestamp, event, error_code, exception_type, route, status_code
| filter event = "error.unexpected" or level = "ERROR"
| sort @timestamp desc
| limit 100
```

Staging validation must confirm that both application groups parse one object
per line, preserve correlation and release version, contain none of the
forbidden fields/values, and retain records for exactly 14 days.
