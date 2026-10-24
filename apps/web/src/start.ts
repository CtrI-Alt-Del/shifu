import { createMiddleware, createStart } from '@tanstack/react-start'

import type { RequestTelemetryContext } from '@/core/shared/interfaces/request-telemetry-context'
import type { SanitizedStackFrame } from '@/core/shared/interfaces/telemetry-provider'
import { getWebTelemetryProvider } from '@/provision/telemetry/console-telemetry-provider'

const UUID_V4_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

export const requestTelemetryMiddleware = createMiddleware().server(
  async ({ next, request }) => {
    const requestId = getRequestId(request.headers.get('X-Request-ID'))
    const telemetry = getWebTelemetryProvider()
    const startedAt = Date.now()
    request.headers.set('X-Request-ID', requestId)
    telemetry.reportVersionOnce(requestId)

    try {
      const result = await next({
        context: { requestId, telemetry } satisfies RequestTelemetryContext,
      })
      const statusCode = result.response.status
      result.response.headers.set('X-Request-ID', requestId)
      telemetry.emit({
        level: statusCode >= 500 ? 'ERROR' : statusCode >= 400 ? 'WARNING' : 'INFO',
        event: statusCode >= 400 ? 'http.request.failed' : 'http.request.completed',
        request_id: requestId,
        method: request.method,
        route: 'unmatched',
        status_code: statusCode,
        duration_ms: Math.max(0, Date.now() - startedAt),
        operation: 'http.request',
        result: statusCode >= 400 ? 'failure' : 'success',
      })
      return result
    } catch (error) {
      telemetry.emit({
        level: 'ERROR',
        event: 'error.unexpected',
        request_id: requestId,
        method: request.method,
        route: 'unmatched',
        duration_ms: Math.max(0, Date.now() - startedAt),
        operation: 'http.request',
        result: 'failure',
        error_code: 'internal_error',
        exception_type: error instanceof Error ? error.name : 'UnknownError',
        stack_trace: sanitizeErrorStack(error),
      })
      throw error
    }
  },
)

// A function middleware keeps the context visible to every createServerFn
// handler while the request middleware remains the single request boundary.
export const serverFunctionTelemetryMiddleware = createMiddleware({
  type: 'function',
}).server(({ next, context }) =>
  next({ context: context as unknown as RequestTelemetryContext }),
)

export const startInstance = createStart(() => ({
  requestMiddleware: [requestTelemetryMiddleware],
  functionMiddleware: [serverFunctionTelemetryMiddleware],
}))

function getRequestId(value: string | null): string {
  return value && UUID_V4_PATTERN.test(value) ? value : crypto.randomUUID()
}

const STACK_COMPONENT_PATTERN = /^[A-Za-z0-9_$.:<>[\]-]{1,120}$/
const STACK_FRAME_PATTERN = /^\s*at\s+(?:(.*?)\s+\()?(.+?):(\d+)(?::\d+)?\)?\s*$/

export function sanitizeErrorStack(
  error: unknown,
): readonly SanitizedStackFrame[] | undefined {
  if (!(error instanceof Error) || typeof error.stack !== 'string') return undefined

  const frames = error.stack.split(/\r?\n/).flatMap((line) => {
    const match = STACK_FRAME_PATTERN.exec(line)
    if (!match) return []

    const [, functionName, location, lineNumber] = match
    const file = location?.split(/[\\/]/).pop()
    const parsedLine = Number.parseInt(lineNumber ?? '', 10)
    if (
      !file ||
      !STACK_COMPONENT_PATTERN.test(file) ||
      !Number.isInteger(parsedLine) ||
      parsedLine < 1
    ) {
      return []
    }

    return [
      {
        file,
        line: parsedLine,
        ...(functionName && STACK_COMPONENT_PATTERN.test(functionName)
          ? { function: functionName }
          : {}),
      },
    ] satisfies SanitizedStackFrame[]
  })

  return frames.length > 0 ? frames.slice(0, 20) : undefined
}
