import { createFileRoute } from '@tanstack/react-router'

import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'

export const Route = createFileRoute('/api/internal/identity/account-closure')({
  server: {
    handlers: {
      POST: ({ request }) => getBetterAuthProvider().closeTechnicalIdentity(request),
    },
  },
})
