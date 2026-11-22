import { createFileRoute } from '@tanstack/react-router'

import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'

export const Route = createFileRoute('/api/identity/browser-data-capabilities/')({
  server: {
    handlers: {
      POST: ({ request }) => getBetterAuthProvider().issueBrowserDataCapability(request),
    },
  },
})
