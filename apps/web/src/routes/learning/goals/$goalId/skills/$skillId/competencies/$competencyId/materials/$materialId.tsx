import { createFileRoute } from '@tanstack/react-router'

import { requireAuthMiddleware } from '@/middlewares/require-auth-middleware'
import { MaterialPage } from '@/ui/learning/widgets/pages/material-page'

export const Route = createFileRoute(
  '/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/materials/$materialId',
)({
  beforeLoad: () => requireAuthMiddleware(),
  component: MaterialRoute,
})

function MaterialRoute() {
  const { competencyId, goalId, materialId, skillId } = Route.useParams()

  return (
    <MaterialPage
      competencyId={competencyId}
      goalId={goalId}
      materialId={materialId}
      skillId={skillId}
    />
  )
}
