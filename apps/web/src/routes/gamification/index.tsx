import { createFileRoute, redirect } from '@tanstack/react-router'

import { ROUTES } from '@/constants/routes'

export const Route = createFileRoute('/gamification/')({
  beforeLoad: () => {
    throw redirect({ to: ROUTES.gamificationOverview, replace: true })
  },
})
