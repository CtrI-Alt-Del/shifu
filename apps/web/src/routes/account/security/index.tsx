import { createFileRoute } from '@tanstack/react-router'

import { AccountSecurityPage } from '@/ui/identity/widgets/pages/account-security-page'

export const Route = createFileRoute('/account/security/')({
  component: AccountSecurityPage,
})
