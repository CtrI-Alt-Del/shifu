import { redirect } from '@tanstack/react-router'
import { createServerFn } from '@tanstack/react-start'
import { getRequest, setResponseHeader } from '@tanstack/react-start/server'

import { serverFunctionTelemetryMiddleware } from '@/start'

import { ROUTES } from '@/constants/routes'
import type { RequestTelemetryContext } from '@/core/shared/interfaces/request-telemetry-context'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'

export type MainPageEntry =
  | { mode: 'public' }
  | {
      mode: 'authenticated'
      account: {
        displayName: string
        email: string
        appearance: 'dark' | 'light' | 'system'
      }
    }

export const enterMainPageMiddleware = createServerFn({ method: 'GET' })
  .middleware([serverFunctionTelemetryMiddleware])
  .handler(async ({ context }: { context: RequestTelemetryContext }) => {
    setResponseHeader('Cache-Control', 'private, no-store')

    const provider = getBetterAuthProvider()
    const request = getRequest()
    const access = await provider.getCurrentAccess(request, context.requestId)

    if (access) {
      await provider.publishMainPageEntered(access, context.requestId)

      return {
        mode: 'authenticated',
        account: {
          displayName: access.displayName,
          email: access.email,
          appearance: access.appearance,
        },
      } satisfies MainPageEntry
    }

    const pendingStatus = await provider.getPendingConfirmationStatus(request)
    if (pendingStatus.hasPendingContext)
      throw redirect({ to: ROUTES.pendingConfirmation })

    return { mode: 'public' } satisfies MainPageEntry
  })
