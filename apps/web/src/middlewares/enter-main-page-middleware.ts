import { createServerFn } from '@tanstack/react-start'
import { redirect } from '@tanstack/react-router'
import { getRequest } from '@tanstack/react-start/server'

import { ROUTES } from '@/constants/routes'
import {
  getBetterAuthProvider,
  type LayoutAccount,
} from '@/provision/auth/better-auth/better-auth-provider'

export const enterMainPageMiddleware = createServerFn({ method: 'GET' }).handler(
  async () => {
    const provider = getBetterAuthProvider()
    const access = await provider.getCurrentAccess(getRequest())

    if (!access) throw redirect({ to: ROUTES.login })

    await provider.publishMainPageEntered(access)
    return {
      displayName: access.displayName,
      email: access.email,
    } satisfies LayoutAccount
  },
)
