import { createFileRoute } from '@tanstack/react-router'

import { GoalCreatePage } from '@/ui/learning/widgets/pages/goal-create-page'
import { requireAuthMiddleware } from '@/middlewares/require-auth-middleware'

export const Route = createFileRoute('/learning/goals/new/')({
  beforeLoad: () => requireAuthMiddleware(),
  component: GoalCreatePage,
})
