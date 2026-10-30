import { createFileRoute } from '@tanstack/react-router'

import { AccountDeletionPage } from '@/ui/identity/widgets/pages/account-deletion-page'

export const Route = createFileRoute('/account/delete/')({
  component: AccountDeletionPage,
})
