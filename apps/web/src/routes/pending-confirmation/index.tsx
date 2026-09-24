import { createFileRoute } from '@tanstack/react-router'

import { PendingConfirmationPage } from '@/ui/identity/widgets/pages/pending-confirmation-page'

export const Route = createFileRoute('/pending-confirmation/')({
  component: PendingConfirmationPage,
})
