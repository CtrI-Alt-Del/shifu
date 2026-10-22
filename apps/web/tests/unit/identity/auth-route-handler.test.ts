import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { RequestTelemetryContext } from '@/core/shared/interfaces/request-telemetry-context'

const auth = vi.hoisted(() => ({ handler: vi.fn() }))

vi.mock('@tanstack/react-router', () => ({
  createFileRoute: () => (options: unknown) => ({ options }),
}))
vi.mock('@/provision/auth/better-auth/better-auth-provider', () => ({
  getBetterAuthProvider: () => auth,
}))

import { Route as authRoute } from '@/routes/api/auth/$'

type AuthRoute = {
  options: {
    server: {
      handlers: {
        GET: (input: {
          request: Request
          context: RequestTelemetryContext
        }) => Promise<Response>
        POST: (input: {
          request: Request
          context: RequestTelemetryContext
        }) => Promise<Response>
      }
    }
  }
}

const context = {
  requestId: '11111111-1111-4111-8111-111111111111',
  telemetry: { emit: vi.fn() },
} satisfies RequestTelemetryContext

function getHandlers() {
  return (authRoute as unknown as AuthRoute).options.server.handlers
}

describe('Better Auth API route handler', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    auth.handler.mockResolvedValue(new Response('{}', { status: 200 }))
  })

  it('forwards the request telemetry ID to Better Auth without mutating the caller request', async () => {
    const request = new Request('http://localhost:7000/api/auth/sign-in/identity', {
      method: 'POST',
      body: JSON.stringify({ email: 'learner@example.test', password: 'secret' }),
    })

    await getHandlers().POST({ request, context })

    const forwardedRequest = auth.handler.mock.calls[0]?.[0] as Request
    expect(forwardedRequest.headers.get('X-Request-ID')).toBe(context.requestId)
    expect(request.headers.get('X-Request-ID')).toBeNull()
    expect(await forwardedRequest.text()).toContain('learner@example.test')
  })

  it('uses the same forwarded telemetry ID for password-recovery requests', async () => {
    const request = new Request('http://localhost:7000/api/auth/password-recovery', {
      method: 'POST',
      body: JSON.stringify({ email: 'learner@example.test' }),
    })

    await getHandlers().POST({ request, context })

    const forwardedRequest = auth.handler.mock.calls[0]?.[0] as Request
    expect(forwardedRequest.headers.get('X-Request-ID')).toBe(context.requestId)
  })

  it('preserves the token endpoint refusal before invoking Better Auth', async () => {
    const response = await getHandlers().GET({
      request: new Request('http://localhost:7000/api/auth/token'),
      context,
    })

    expect(response.status).toBe(404)
    expect(auth.handler).not.toHaveBeenCalled()
  })
})
