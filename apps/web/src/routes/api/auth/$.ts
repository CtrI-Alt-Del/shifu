import { createFileRoute } from '@tanstack/react-router'

import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'

function handleAuthRequest(request: Request) {
  const pathname = new URL(request.url).pathname.replace(/\/+$/, '')

  if (pathname === '/api/auth/token') return new Response(null, { status: 404 })

  return getBetterAuthProvider().handler(request)
}

export const Route = createFileRoute('/api/auth/$')({
  server: {
    handlers: {
      GET: ({ request }) => handleAuthRequest(request),
      POST: ({ request }) => handleAuthRequest(request),
    },
  },
})
