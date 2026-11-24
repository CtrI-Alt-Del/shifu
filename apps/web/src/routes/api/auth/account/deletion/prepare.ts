import { createFileRoute } from '@tanstack/react-router'

import { handleAuthRequest } from '@/routes/api/auth/$'

export const Route = createFileRoute('/api/auth/account/deletion/prepare')({
  server: {
    handlers: {
      POST: ({ request, context }) => handleAuthRequest(request, context, 201),
    },
  },
})
