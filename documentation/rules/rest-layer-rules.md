---
description: REST controller, route grouping, dependency wiring, and REST client rules.
---

# REST Wiring Rules

These rules apply to NestJS controllers under `apps/server/src` and their matching
files under `apps/server/rest-client`.

## Grouped routes use a module decorator

Every route group must have a decorator in the owning module's `decorators`
directory. The decorator centralizes the route prefix:

```ts
// decorators/intakes-controller.ts
export const IntakesController = () => Controller('intakes')
```

Controllers in that group use `@IntakesController()` instead of repeating
`@Controller('intakes')`.

## Route parameters use semantic names

Every dynamic route segment must identify the resource or relationship it
represents. Use names such as `:clientId`, `:collaboratorId`, `:intakeId` and
`:legalAreaId`; never use a generic `:id`. The controller's `@Param()` key and
the local variable must match the route placeholder exactly, and REST examples,
tests and documentation must preserve the same name.

## One controller represents one application action

Create one controller class per use case or REST action. A controller must only:

- receive and extract HTTP input;
- translate that input into the use-case request;
- execute the use case;
- return its result.

Validation, domain decisions, persistence access, and mapping persisted rows do
not belong in controllers.

## Controllers instantiate use cases once

A controller constructor receives the dependencies required by its use case and
manually instantiates a private, readonly use-case field:

```ts
@IntakesController()
export class ListClientIntakesController {
  private readonly useCase: ListClientIntakesUseCase

  constructor(
    @Inject(INTAKE_REPOSITORIES.intakes)
    intakesRepository: IntakesRepository,
  ) {
    this.useCase = new ListClientIntakesUseCase(intakesRepository)
  }

  @Get('clients/:clientId')
  handle(@Param('clientId') clientId: string) {
    return this.useCase.execute({ clientId })
  }
}
```

Do not inject a use-case class through NestJS and do not instantiate it inside
`handle`. The constructor receives use-case dependencies, not the use case itself.

Repositories must be injected through the module token and typed with the core
interface. Never inject a concrete infrastructure implementation into a
controller. Shared providers such as `DatetimeProvider` are regular constructor
dependencies.

## Request body types come from the use case

When a controller receives a body, declare only a local `RequestBody` type and
derive it from the use-case `execute` method:

```ts
type RequestBody = Parameters<RegisterIntakeUseCase['execute']>[0]
```

Use it directly in the body parameter:

```ts
handle(@Body() body: RequestBody) {
  return this.useCase.execute(body)
}
```

If a use-case request also contains route or query parameters, derive
`RequestBody` with `Omit` and assemble the complete request in `handle`. Do not
duplicate a request DTO shape that already exists in the use case.

Do not declare aliases such as `RequestParams`, `RequestQuery`, or
`ControllerRequest` merely to rename primitive route inputs. Type those parameters
directly unless a framework DTO is required for validation or transformation.

## Controllers document HTTP responses

Every controller action must declare its successful response and each expected
error response with NestJS Swagger `@ApiResponse` decorators. Use `HttpStatus`
constants instead of numeric literals, write a concise description, and provide
the response DTO through `type` whenever the response has a JSON body. Standard
REST errors use `ErrorResponseDto`:

```ts
@ApiResponse({
  status: HttpStatus.OK,
  description: 'The client was returned successfully.',
  type: ClientDetailsResponseDto,
})
@ApiResponse({
  status: HttpStatus.NOT_FOUND,
  description: 'The client was not found.',
  type: ErrorResponseDto,
})
handle() {
  // ...
}
```

Keep the documented statuses synchronized with the global REST error handler and
the use case behavior. Responses without a body may omit `type`; all other
successful and error responses must describe their payload explicitly.

## Routes reflect resource ownership

Use nested route segments when listing a resource by its owner. For client
intakes, the route is:

```http
GET /intakes/clients/:clientId
```

The route-group prefix remains first, followed by the owner collection and its
identifier. Keep path names plural for collections.

## Every route group has a REST client file

Each controller route group must have a matching `.rest` file under:

```text
apps/server/rest-client/<module>/<route-group>.rest
```

For the `intakes` group, use:

```text
apps/server/rest-client/intake/intakes.rest
```

The file must cover every controller route in that group. Define the base URL and
reusable identifiers once, separate requests with `###`, and give each request a
clear label.

Include the actual method, route parameters, required headers, and a representative
JSON body. Keep the examples synchronized whenever a controller route or request
shape changes.

## Services implement REST contracts

Each client-facing module service must implement the service interface declared in
the core package. The interface belongs under the module's `interfaces` directory
and describes the operation names, request types, and `RestResponse` payloads.

For example, Identity exposes its REST contract from
`packages/core/src/identity/interfaces/identity-service.ts`:

```ts
export interface IdentityService {
  getClient(clientId: string): Promise<RestResponse<ClientDetails>>
  lookupClient(request: LookupClientRequest): Promise<RestResponse<ClientDetails>>
  registerClient(request: RegisterClientRequest): Promise<RestResponse<ClientDetails>>
}
```

Implementations belong in the application adapter layer, under
`apps/web/src/rest/services/<module>-service.ts`. They must:

- receive a `RestClient` instead of creating an Axios or `fetch` client directly;
- return the core service contract;
- delegate each operation to the controller's HTTP method and route;
- pass route identifiers in the path and request data in the body;
- preserve the typed response body without reimplementing use-case rules;
- contain no business decisions, authentication state, caching, or persistence
  logic.

Use a factory so the transport dependency can be replaced in tests or configured
at the application boundary:

```ts
import type { IdentityService as IdentityRestService } from '@hms/core/identity/interfaces'
import type { ClientDetails } from '@hms/core/identity/domain/entities'
import type { RestClient } from '@hms/core/shared/interfaces'

export const IdentityService = (restClient: RestClient): IdentityRestService => {
  return {
    getClient(clientId) {
      return restClient.get<ClientDetails>(`/clients/${clientId}`)
    },

    lookupClient(request) {
      return restClient.post<ClientDetails>('/clients/lookup', request)
    },

    registerClient(request) {
      return restClient.post<ClientDetails>('/clients', request)
    },
  }
}
```

The service method names and signatures must remain aligned with the core
interface. Changes to a controller route or payload require updating the core
contract and its application adapter together.

## Web REST transport owns cookie transport

`apps/web/src/rest/axios/axios-rest-client.ts` is the web transport boundary. It
sends credentialed requests so the browser can attach the server-issued
`HttpOnly` session cookie. It must not read a token, inject a Bearer header, or
persist authentication material. Web module services must not import Better
Auth, read the auth context, or assemble authentication headers themselves.

When the web server performs an authenticated SSR request, its transport must
forward the incoming session cookie explicitly. The browser and SSR paths must
resolve the same `/auth/session` contract without exposing the cookie to client
JavaScript.

The REST context belongs under `apps/web/src/ui/shared/contexts/rest-context/` and
may depend on the shared auth context for authenticated application state. Keep
Better Auth operations in the auth provider/context boundary and keep cookie
transport behavior in the REST client.

Cookie-authenticated unsafe methods require exact trusted-origin CORS and server
`Origin` validation. `SameSite` cookies are a defense in depth control, not a
replacement for origin validation or application authorization.

When a service factory is added or changed, verify its HTTP mapping at the
appropriate REST boundary with the existing workspace validation commands.

Web module services do not receive dedicated test files. Verify their observable
method, path, query, body, response and failure behavior through the consuming
widget/page tests and Playwright route integration suite. Server controller tests
remain the authoritative backend HTTP contract boundary. Do not create or retain
`apps/web/src/rest/services/tests/<module>-service.test.ts` merely to mock
`RestClient` and restate delegation calls.

## Server imports use aliases

Imports between files inside `apps/server/src` must use the `@/` prefix. External
package imports such as `@nestjs/common` and `@hms/core/...` keep their package
paths.

## Shared errors use one global REST handler

The server must register one global error handler during bootstrap. The handler
belongs under `apps/server/src/shared/rest/filters` and must map core shared
errors to HTTP status codes without putting HTTP concerns in `packages/core`:

- `NotFoundError` becomes `404`;
- `ConflictError` becomes `409`;
- other `AppError` instances become `500`.

The response shape is stable and contains `statusCode`, `title`, `message`,
`timestamp`, and `path`. Unknown errors must return a generic internal-error
message and must not expose implementation details.
