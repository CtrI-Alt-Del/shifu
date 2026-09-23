import { notFound, createFileRoute } from '@tanstack/react-router'

import { requireAuthMiddleware } from '@/middlewares/require-auth-middleware'

export const Route = createFileRoute('/learning/goals/$goalId/skills/$skillId/')({
  beforeLoad: () => requireAuthMiddleware(),
  loader: () => {
    throw notFound()
  },
})
