import { createFileRoute } from '@tanstack/react-router'

import { GamificationPage } from '@/ui/gamification/widgets/pages/gamification-page'
import { requireAuthMiddleware } from '@/middlewares/require-auth-middleware'

export const Route = createFileRoute('/gamification/')({
  beforeLoad: () => requireAuthMiddleware(),
  component: GamificationPage,
})
