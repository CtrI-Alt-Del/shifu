import { redirect } from '@tanstack/react-router'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'

import { ROUTES } from '@/constants/routes'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'

export const requireAuthMiddleware = createServerFn({ method: 'GET' }).handler(
  async () => {
    const access = await getBetterAuthProvider().getCurrentAccess(getRequest())

    if (!access) throw redirect({ to: ROUTES.login })

    return undefined
  },
)
