import { createFileRoute } from '@tanstack/react-router'

import { StreakReminderCard } from '@/ui/gamification/widgets/components/streak-reminder-card'
import { AccountProfilePage } from '@/ui/identity/widgets/pages/account-profile-page'

export const Route = createFileRoute('/account/profile/')({
  component: AccountProfileRoute,
})

function AccountProfileRoute() {
  const { email } = Route.useRouteContext()
  return (
    <AccountProfilePage accountEmail={email} remindersCard={<StreakReminderCard />} />
  )
}
