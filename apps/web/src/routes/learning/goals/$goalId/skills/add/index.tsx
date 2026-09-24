import { createFileRoute } from '@tanstack/react-router'

import { requireAuthMiddleware } from '@/middlewares/require-auth-middleware'
import { GoalSkillAddPage } from '@/ui/learning/widgets/pages/goal-skill-add-page'

export const Route = createFileRoute('/learning/goals/$goalId/skills/add/')({
  beforeLoad: () => requireAuthMiddleware(),
  component: RouteComponent,
})

function RouteComponent() {
  const { goalId } = Route.useParams()

  return <GoalSkillAddPage goalId={goalId} />
}
