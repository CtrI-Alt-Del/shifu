import { createFileRoute } from '@tanstack/react-router'

import { RegisterPage } from '@/ui/identity/widgets/pages/register-page'

export const Route = createFileRoute('/register/')({ component: RegisterPage })
