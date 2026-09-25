import { useLocation, useMatches } from '@tanstack/react-router'

import { ROUTES } from '@/constants/routes'
import type { LayoutAccount } from '../app-layout/account-menu'

export const PUBLIC_ROUTE_PATHS = [
  ROUTES.login,
  ROUTES.register,
  ROUTES.forgotPassword,
  ROUTES.pendingConfirmation,
  ROUTES.confirmEmail,
] as const

export function isPublicRoute(pathname: string): boolean {
  const normalizedPathname = pathname.replace(/\/+$/, '') || ROUTES.root

  return PUBLIC_ROUTE_PATHS.some((route) => {
    const normalizedRoute = route.replace(/\/+$/, '') || ROUTES.root
    return normalizedPathname === normalizedRoute
  })
}

export function useRootLayout(): {
  account?: LayoutAccount
  isPublic: boolean
} {
  const location = useLocation()
  const matches = useMatches()
  const isPublic = isPublicRoute(location.pathname)
  const account = isPublic ? undefined : findLayoutAccount(matches)

  return {
    account,
    isPublic,
  }
}

function findLayoutAccount(
  matches: readonly { context: unknown }[],
): LayoutAccount | undefined {
  for (let index = matches.length - 1; index >= 0; index -= 1) {
    const context = matches[index]?.context

    if (isLayoutAccount(context)) return context
  }

  return undefined
}

function isLayoutAccount(value: unknown): value is LayoutAccount {
  if (typeof value !== 'object' || value === null) return false

  const account = value as Record<string, unknown>

  return typeof account.displayName === 'string' && typeof account.email === 'string'
}
