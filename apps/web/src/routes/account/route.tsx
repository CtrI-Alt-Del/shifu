import { Outlet, createFileRoute } from '@tanstack/react-router'

import { AccountLayout } from '@/ui/identity/widgets/layouts/account-layout'
import { requireAuthMiddleware } from '@/middlewares/require-auth-middleware'

export const Route = createFileRoute('/account')({
  beforeLoad: () => requireAuthMiddleware(),
  component: () => (
    <AccountLayout>
      <Outlet />
    </AccountLayout>
  ),
})
