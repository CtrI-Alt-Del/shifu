import { createFileRoute } from '@tanstack/react-router'

import { GoalCreatePlaceholderPage } from '@/ui/learning/widgets/pages/goal-create-placeholder-page'
import { requireAuthMiddleware } from '@/middlewares/require-auth-middleware'

export const Route = createFileRoute('/learning/goals/new/')({
  beforeLoad: () => requireAuthMiddleware(),
  component: GoalCreatePlaceholderPage,
})
