import { createFileRoute, redirect } from '@tanstack/react-router'

import { ROUTES } from '@/constants/routes'

export const Route = createFileRoute('/account/')({
  beforeLoad: () => {
    throw redirect({ to: ROUTES.accountProfile, replace: true })
  },
})
