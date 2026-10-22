import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { RequestTelemetryContext } from '@/core/shared/interfaces/request-telemetry-context'

const telemetry = vi.hoisted(() => ({
  emit: vi.fn(),
  reportVersionOnce: vi.fn(),
}))

vi.mock('@/provision/telemetry/console-telemetry-provider', () => ({
  getWebTelemetryProvider: () => telemetry,
}))

import {
  requestTelemetryMiddleware,
  sanitizeErrorStack,
  serverFunctionTelemetryMiddleware,
} from '@/start'

type RequestMiddleware = {
  options: {
    server: (input: {
      request: Request
      next: (input: {
        context: RequestTelemetryContext
      }) => Promise<{ response: Response }>
    }) => Promise<{ response: Response }>
  }
}

type FunctionMiddleware = {
  options: {
    server: (input: {
      context: RequestTelemetryContext
      next: (input: { context: RequestTelemetryContext }) => Promise<unknown>
    }) => Promise<unknown>
  }
}

const requestHandler = (requestTelemetryMiddleware as unknown as RequestMiddleware)
  .options.server

describe('Web request telemetry boundary', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('retains a valid request ID, passes typed context and echoes the response ID', async () => {
    const requestId = '11111111-1111-4111-8111-111111111111'
    const result = await requestHandler({
      request: new Request('http://localhost:7000/api/auth/get-session', {
        headers: { 'X-Request-ID': requestId },
      }),
      next: async ({ context }) => {
        expect(context.requestId).toBe(requestId)
        expect(context.telemetry).toBe(telemetry)
        return { response: new Response(null, { status: 204 }) }
      },
    })

    expect(result.response.headers.get('X-Request-ID')).toBe(requestId)
    expect(telemetry.reportVersionOnce).toHaveBeenCalledWith(requestId)
    expect(telemetry.emit).toHaveBeenCalledWith(
      expect.objectContaining({
        event: 'http.request.completed',
        request_id: requestId,
        status_code: 204,
      }),
    )
  })

  it('generates a safe ID and records bounded sanitized frames for unexpected errors', async () => {
    const error = new Error('raw password=secret message')
    error.stack =
      'Error: raw password=secret message\n' +
      '    at handleAuthRequest (C:\\private\\auth.ts:17:4)\n' +
      '    at C:\\private\\server.ts:22:2'

    await expect(
      requestHandler({
        request: new Request('http://localhost:7000/api/auth/get-session', {
          headers: { 'X-Request-ID': 'malformed-secret-token' },
        }),
        next: async () => {
          throw error
        },
      }),
    ).rejects.toBe(error)

    const event = telemetry.emit.mock.calls.find(
      ([value]) => value.event === 'error.unexpected',
    )?.[0]
    expect(event).toMatchObject({
      error_code: 'internal_error',
      stack_trace: [
        { file: 'auth.ts', line: 17, function: 'handleAuthRequest' },
        { file: 'server.ts', line: 22 },
      ],
    })
    expect(JSON.stringify(event)).not.toContain('raw password=secret message')
    expect(JSON.stringify(event)).not.toContain('C:\\private')
    expect(event.request_id).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
    )
  })

  it('limits parsed stack frames to the telemetry bound', () => {
    const error = new Error('hidden')
    error.stack = Array.from(
      { length: 25 },
      (_, index) => `    at handler (C:\\private\\file-${index}.ts:${index + 1}:1)`,
    ).join('\n')

    expect(sanitizeErrorStack(error)).toHaveLength(20)
  })

  it('forwards function middleware context unchanged', async () => {
    const functionMiddleware = (
      serverFunctionTelemetryMiddleware as unknown as FunctionMiddleware
    ).options.server
    const context = { requestId: '11111111-1111-4111-8111-111111111111', telemetry }
    const next = vi.fn(async () => ({ response: new Response(null, { status: 200 }) }))

    await functionMiddleware({ context, next: next as never })

    expect(next).toHaveBeenCalledWith({ context })
  })
})
