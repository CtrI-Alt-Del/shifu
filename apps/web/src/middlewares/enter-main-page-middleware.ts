import { createServerFn } from '@tanstack/react-start'
import { serverFunctionTelemetryMiddleware } from '@/start'
import { redirect } from '@tanstack/react-router'
import { getRequest } from '@tanstack/react-start/server'

import { ROUTES } from '@/constants/routes'
import type { RequestTelemetryContext } from '@/core/shared/interfaces/request-telemetry-context'
import {
  getBetterAuthProvider,
  type LayoutAccount,
} from '@/provision/auth/better-auth/better-auth-provider'

export const enterMainPageMiddleware = createServerFn({ method: 'GET' })
  .middleware([serverFunctionTelemetryMiddleware])
  .handler(async ({ context }: { context: RequestTelemetryContext }) => {
    const provider = getBetterAuthProvider()
    const access = await provider.getCurrentAccess(getRequest(), context.requestId)

    if (!access) throw redirect({ to: ROUTES.login })

    await provider.publishMainPageEntered(access, context.requestId)

    return {
      displayName: access.displayName,
      email: access.email,
    } satisfies LayoutAccount
  })
