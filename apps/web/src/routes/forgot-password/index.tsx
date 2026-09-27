import { createFileRoute } from '@tanstack/react-router'

import { ForgotPasswordPage } from '@/ui/identity/widgets/pages/forgot-password-page'

export const Route = createFileRoute('/forgot-password/')({
  component: ForgotPasswordPage,
})
