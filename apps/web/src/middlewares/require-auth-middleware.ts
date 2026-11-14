import { redirect } from '@tanstack/react-router'
import { createServerFn } from '@tanstack/react-start'
import { serverFunctionTelemetryMiddleware } from '@/start'
import { getRequest } from '@tanstack/react-start/server'

import { ROUTES } from '@/constants/routes'
import type { RequestTelemetryContext } from '@/core/shared/interfaces/request-telemetry-context'
import {
  getBetterAuthProvider,
  type LayoutAccount,
} from '@/provision/auth/better-auth/better-auth-provider'

export const requireAuthMiddleware = createServerFn({ method: 'GET' })
  .middleware([serverFunctionTelemetryMiddleware])
  .handler(async ({ context }: { context: RequestTelemetryContext }) => {
    const access = await getBetterAuthProvider().getCurrentAccess(
      getRequest(),
      context.requestId,
    )

    if (!access) throw redirect({ to: ROUTES.login })

    return {
      displayName: access.displayName,
      email: access.email,
    } satisfies LayoutAccount
  })
