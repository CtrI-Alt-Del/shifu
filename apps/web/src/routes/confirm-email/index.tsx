import { createFileRoute } from '@tanstack/react-router'

import { ConfirmEmailPage } from '@/ui/identity/widgets/pages/confirm-email-page'

export const Route = createFileRoute('/confirm-email/')({
  validateSearch: (search: Record<string, unknown>) => ({
    token: typeof search.token === 'string' ? search.token : undefined,
  }),
  component: ConfirmEmailRoute,
})

function ConfirmEmailRoute() {
  const { token } = Route.useSearch()
  return <ConfirmEmailPage token={token} />
}
