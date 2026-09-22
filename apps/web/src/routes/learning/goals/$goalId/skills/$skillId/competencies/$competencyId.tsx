import { Outlet, createFileRoute, useRouterState } from '@tanstack/react-router'

import { requireAuthMiddleware } from '@/middlewares/require-auth-middleware'
import { CompetencyDetailPage } from '@/ui/learning/widgets/pages/competency-detail-page'

export const Route = createFileRoute(
  '/learning/goals/$goalId/skills/$skillId/competencies/$competencyId',
)({
  beforeLoad: () => requireAuthMiddleware(),
  component: CompetencyDetailRoute,
})

function CompetencyDetailRoute() {
  const { competencyId, goalId, skillId } = Route.useParams()
  const activeRouteId = useRouterState({
    select: (state) => state.matches.at(-1)?.routeId,
  })

  if (activeRouteId !== Route.id) return <Outlet />

  return (
    <CompetencyDetailPage competencyId={competencyId} goalId={goalId} skillId={skillId} />
  )
}
