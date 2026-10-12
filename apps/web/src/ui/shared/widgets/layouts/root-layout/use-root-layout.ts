import type { MentorContextHint } from '@/core/intelligence/mentor-response'
import { useLocation, useMatches } from '@tanstack/react-router'

import { ROUTES } from '@/constants/routes'
import type { LayoutAccount } from '../app-layout/account-menu'

export const PUBLIC_ROUTE_PATHS = [
  ROUTES.login,
  ROUTES.register,
  ROUTES.forgotPassword,
  ROUTES.resetPassword,
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
  mentorContextHint: MentorContextHint | null
} {
  const location = useLocation()
  const matches = useMatches()
  const isPublic = isPublicRoute(location.pathname)
  const account = isPublic ? undefined : findLayoutAccount(matches)

  return {
    account,
    isPublic,
    mentorContextHint: location.pathname.startsWith('/learning/goals/')
      ? findMentorContextHint(matches)
      : null,
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

function findMentorContextHint(
  matches: readonly { params?: unknown }[],
): MentorContextHint | null {
  const params = Object.assign(
    {},
    ...matches.map((match) => match.params ?? {}),
  ) as Record<string, unknown>
  function identifier(name: string) {
    return typeof params[name] === 'string' &&
      /^[0-9A-HJKMNP-TV-Z]{26}$/.test(params[name])
      ? params[name]
      : null
  }
  const goalId = identifier('goalId')
  if (!goalId) return null
  return {
    goalId,
    skillId: identifier('skillId'),
    competencyId: identifier('competencyId'),
    materialId: identifier('materialId'),
    activityId: identifier('activityId'),
  }
}
