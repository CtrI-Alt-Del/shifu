import { createFileRoute } from '@tanstack/react-router'

import { LearningPage } from '@/ui/learning/widgets/pages/learning-page'
import { requireAuthMiddleware } from '@/middlewares/require-auth-middleware'

export const Route = createFileRoute('/learning/')({
  beforeLoad: () => requireAuthMiddleware(),
  component: LearningPage,
})
