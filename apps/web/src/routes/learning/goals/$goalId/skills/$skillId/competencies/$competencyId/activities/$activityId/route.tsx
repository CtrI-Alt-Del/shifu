import { Outlet, createFileRoute } from '@tanstack/react-router'

import { requireAuthMiddleware } from '@/middlewares/require-auth-middleware'

export const Route = createFileRoute(
  '/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId',
)({
  beforeLoad: () => requireAuthMiddleware(),
  component: () => <Outlet />,
})
