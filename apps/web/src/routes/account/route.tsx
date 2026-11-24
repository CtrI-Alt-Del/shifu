import { Outlet, createFileRoute } from '@tanstack/react-router'
import { redirect } from '@tanstack/react-router'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'

import { ROUTES } from '@/constants/routes'
import type { RequestTelemetryContext } from '@/core/shared/interfaces/request-telemetry-context'
import { serverFunctionTelemetryMiddleware } from '@/start'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { AccountLayout } from '@/ui/identity/widgets/layouts/account-layout'
import { AccountDeletionStatusPage } from '@/ui/identity/widgets/pages/account-deletion-page'

const requireAccountAccessOrDeletionStatus = createServerFn({ method: 'GET' })
  .middleware([serverFunctionTelemetryMiddleware])
  .handler(async ({ context }: { context: RequestTelemetryContext }) => {
    const request = getRequest()
    const provider = getBetterAuthProvider()
    const access = await provider.getCurrentAccess(request, context.requestId)
    if (access) {
      return {
        accountDeletionStatus: null,
        displayName: access.displayName,
        email: access.email,
        appearance: access.appearance,
      }
    }

    const pathname = new URL(request.url).pathname.replace(/\/+$/, '')
    if (pathname === ROUTES.accountDelete) {
      const accountDeletionStatus = await provider
        .getAccountDeletionStatus(request)
        .catch(() => null)
      if (accountDeletionStatus) {
        return {
          accountDeletionStatus,
          displayName: '',
          email: '',
        }
      }
    }

    throw redirect({ to: ROUTES.login })
  })

export const Route = createFileRoute('/account')({
  beforeLoad: () => requireAccountAccessOrDeletionStatus(),
  component: () => {
    const { accountDeletionStatus } = Route.useRouteContext()
    if (accountDeletionStatus) {
      return <AccountDeletionStatusPage status={accountDeletionStatus} />
    }
    return (
      <AccountLayout>
        <Outlet />
      </AccountLayout>
    )
  },
})
