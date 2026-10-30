import { createFileRoute } from '@tanstack/react-router'

import { AccountProfilePage } from '@/ui/identity/widgets/pages/account-profile-page'

export const Route = createFileRoute('/account/profile/')({
  component: AccountProfileRoute,
})

function AccountProfileRoute() {
  const { email } = Route.useRouteContext()
  return <AccountProfilePage accountEmail={email} />
}
