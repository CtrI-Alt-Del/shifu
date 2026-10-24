import { Outlet, createFileRoute } from '@tanstack/react-router'

import { GamificationLayout } from '@/ui/gamification/widgets/layouts/gamification-layout'
import { requireAuthMiddleware } from '@/middlewares/require-auth-middleware'

export const Route = createFileRoute('/gamification')({
  beforeLoad: () => requireAuthMiddleware(),
  component: () => (
    <GamificationLayout>
      <Outlet />
    </GamificationLayout>
  ),
})
