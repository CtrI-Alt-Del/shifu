import { createFileRoute } from '@tanstack/react-router'

import { PlannerPlaceholderPage } from '@/ui/intelligence/widgets/pages/planner-placeholder-page'
import { requireAuthMiddleware } from '@/middlewares/require-auth-middleware'

export const Route = createFileRoute('/intelligence/planner/$planningId/')({
  beforeLoad: () => requireAuthMiddleware(),
  component: RouteComponent,
})

function RouteComponent() {
  const { planningId } = Route.useParams()

  return <PlannerPlaceholderPage planningId={planningId} />
}
