import { createFileRoute } from '@tanstack/react-router'

import { GoalDetailPage } from '@/ui/learning/widgets/pages/goal-detail-page'
import { requireAuthMiddleware } from '@/middlewares/require-auth-middleware'

export const Route = createFileRoute('/learning/goals/$goalId/')({
  beforeLoad: () => requireAuthMiddleware(),
  component: RouteComponent,
})

function RouteComponent() {
  const { goalId } = Route.useParams()

  return <GoalDetailPage goalId={goalId} />
}
