import { createFileRoute } from '@tanstack/react-router'

import { requireAuthMiddleware } from '@/middlewares/require-auth-middleware'
import { SkillPage } from '@/ui/learning/widgets/pages/skill-page'

export const Route = createFileRoute('/learning/goals/$goalId/skills/$skillId/')({
  beforeLoad: () => requireAuthMiddleware(),
  component: SkillRoute,
})

function SkillRoute() {
  const ids = Route.useParams()
  return <SkillPage {...ids} />
}
