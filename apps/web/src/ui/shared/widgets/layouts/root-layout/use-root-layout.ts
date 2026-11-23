import type { MentorContextHint } from '@/core/intelligence/mentor-response'
import { useLocation, useMatches } from '@tanstack/react-router'
import { useEffect, useState } from 'react'

import { ROUTES } from '@/constants/routes'
import {
  ACCOUNT_APPEARANCES,
  type AccountAppearance,
} from '@/core/identity/account-appearance'
import type { LayoutAccount } from '../app-layout/account-menu'

export const PUBLIC_ROUTE_PATHS = [
  ROUTES.login,
  ROUTES.register,
  ROUTES.forgotPassword,
  ROUTES.resetPassword,
  ROUTES.pendingConfirmation,
  ROUTES.confirmEmail,
  ROUTES.privacy,
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
  isHydrated: boolean
  isPublic: boolean
  mentorContextHint: MentorContextHint | null
  theme: AccountAppearance
} {
  const location = useLocation()
  const matches = useMatches()
  const [isHydrated, setIsHydrated] = useState(false)
  const rootEntry = findMainPageEntry(matches)
  const isPublic = isPublicRoute(location.pathname) || rootEntry?.mode === 'public'
  const account = isPublic
    ? undefined
    : rootEntry?.mode === 'authenticated'
      ? rootEntry.account
      : findLayoutAccount(matches)

  useEffect(() => {
    setIsHydrated(true)
  }, [])

  return {
    account,
    isHydrated,
    isPublic,
    mentorContextHint: location.pathname.startsWith('/learning/goals/')
      ? findMentorContextHint(matches)
      : null,
    theme: isPublic ? 'dark' : resolveAccountTheme(account),
  }
}

function resolveAccountTheme(account: LayoutAccount | undefined): AccountAppearance {
  const appearance = account?.appearance

  return ACCOUNT_APPEARANCES.find((value) => value === appearance) ?? 'system'
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

type MainPageEntry =
  | { mode: 'public' }
  | { mode: 'authenticated'; account: LayoutAccount }

function findMainPageEntry(
  matches: readonly { context: unknown }[],
): MainPageEntry | undefined {
  for (let index = matches.length - 1; index >= 0; index -= 1) {
    const context = matches[index]?.context
    if (!isRecord(context)) continue

    if (context.mode === 'public') return { mode: 'public' }
    if (context.mode === 'authenticated' && isLayoutAccount(context.account)) {
      return { mode: 'authenticated', account: context.account }
    }
  }

  return undefined
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
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
