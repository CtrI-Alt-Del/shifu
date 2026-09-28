import { createFileRoute } from '@tanstack/react-router'

import { ResetPasswordPage } from '@/ui/identity/widgets/pages/reset-password-page'

export const Route = createFileRoute('/reset-password/')({
  validateSearch: (search: Record<string, unknown>) => ({
    token: typeof search.token === 'string' ? search.token : undefined,
  }),
  component: ResetPasswordRoute,
})

function ResetPasswordRoute() {
  const search = Route.useSearch()
  const token =
    'token' in search && typeof search.token === 'string' ? search.token : undefined
  return <ResetPasswordPage token={token} />
}
