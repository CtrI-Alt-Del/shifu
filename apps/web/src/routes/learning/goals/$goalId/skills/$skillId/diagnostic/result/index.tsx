import { createFileRoute } from '@tanstack/react-router'

import { requireAuthMiddleware } from '@/middlewares/require-auth-middleware'
import { DiagnosticResultPage } from '@/ui/learning/widgets/pages/diagnostic-result-page'

export const Route = createFileRoute(
  '/learning/goals/$goalId/skills/$skillId/diagnostic/result/',
)({
  beforeLoad: () => requireAuthMiddleware(),
  component: DiagnosticResultRoute,
})

function DiagnosticResultRoute() {
  const ids = Route.useParams()

  return <DiagnosticResultPage {...ids} />
}
