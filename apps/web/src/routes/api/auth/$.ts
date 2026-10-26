import { createFileRoute } from '@tanstack/react-router'

import type { RequestTelemetryContext } from '@/core/shared/interfaces/request-telemetry-context'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'

async function handleAuthRequest(
  request: Request,
  context: RequestTelemetryContext | undefined,
) {
  const pathname = new URL(request.url).pathname.replace(/\/+$/, '')

  if (pathname === '/api/auth/token') return new Response(null, { status: 404 })

  const requestId =
    context?.requestId ?? request.headers.get('X-Request-ID') ?? crypto.randomUUID()
  const headers = new Headers(request.headers)
  headers.set('X-Request-ID', requestId)
  const init: RequestInit & { duplex?: 'half' } = {
    method: request.method,
    headers,
    redirect: request.redirect,
    signal: request.signal,
  }

  if (request.method !== 'GET' && request.method !== 'HEAD') {
    init.body = request.body
    init.duplex = 'half'
  }

  const response = await getBetterAuthProvider().handler(new Request(request.url, init))
  if (pathname === '/api/auth/account' || pathname.startsWith('/api/auth/account/')) {
    response.headers.set('Cache-Control', 'no-store')
  }
  return response
}

export const Route = createFileRoute('/api/auth/$')({
  server: {
    handlers: {
      GET: ({ request, context }) => handleAuthRequest(request, context),
      POST: ({ request, context }) => handleAuthRequest(request, context),
    },
  },
})
