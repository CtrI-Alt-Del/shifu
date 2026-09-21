import { createFileRoute } from '@tanstack/react-router'

import { AccountPage } from '@/ui/identity/widgets/pages/account-page'
import { requireAuthMiddleware } from '@/middlewares/require-auth-middleware'

export const Route = createFileRoute('/account/')({
  beforeLoad: () => requireAuthMiddleware(),
  component: AccountPage,
})
