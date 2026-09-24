import { createFileRoute, redirect } from '@tanstack/react-router'

import { ROUTES } from '@/constants/routes'
import { requireAuthMiddleware } from '@/middlewares/require-auth-middleware'

export const Route = createFileRoute('/learning/')({
  beforeLoad: async () => {
    await requireAuthMiddleware()
    throw redirect({ replace: true, to: ROUTES.root })
  },
})
