import { createFileRoute } from '@tanstack/react-router'

import { handleAuthRequest } from '@/routes/api/auth/$'

export const Route = createFileRoute('/api/auth/account/deletion/')({
  server: {
    handlers: {
      GET: ({ request, context }) => handleAuthRequest(request, context),
      POST: ({ request, context }) => handleAuthRequest(request, context, 202),
    },
  },
})
