import { createFileRoute } from '@tanstack/react-router'

import { SignInPage } from '@/ui/identity/widgets/pages/sign-in-page'

export const Route = createFileRoute('/login/')({ component: SignInPage })
