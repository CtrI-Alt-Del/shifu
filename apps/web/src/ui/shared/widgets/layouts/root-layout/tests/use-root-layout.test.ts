import { describe, expect, it } from 'vitest'

import { isPublicRoute } from '../use-root-layout'

describe('useRootLayout route classification', () => {
  it('classifies every public contract path without treating protected paths as public', () => {
    expect(isPublicRoute('/login/')).toBe(true)
    expect(isPublicRoute('/register')).toBe(true)
    expect(isPublicRoute('/forgot-password/')).toBe(true)
    expect(isPublicRoute('/reset-password')).toBe(true)
    expect(isPublicRoute('/pending-confirmation')).toBe(true)
    expect(isPublicRoute('/confirm-email')).toBe(true)
    expect(isPublicRoute('/privacy')).toBe(true)
    expect(isPublicRoute('/privacy/')).toBe(true)
    expect(isPublicRoute('/account')).toBe(false)
    expect(isPublicRoute('/')).toBe(false)
  })
})

import { renderHook } from '@testing-library/react'
import { vi } from 'vitest'
import { useRootLayout } from '../use-root-layout'
const routing = vi.hoisted(() => ({
  pathname: '/',
  matches: [] as { context: unknown; params?: unknown }[],
}))
vi.mock('@tanstack/react-router', () => ({
  useLocation: () => ({ pathname: routing.pathname }),
  useMatches: () => routing.matches,
}))
it('uses the public root mode without an authenticated layout account', () => {
  routing.pathname = '/'
  routing.matches = [{ context: { mode: 'public' } }]

  const { result } = renderHook(useRootLayout)

  expect(result.current.isPublic).toBe(true)
  expect(result.current.account).toBeUndefined()
  expect(result.current.theme).toBe('dark')
})

it('uses the authenticated root mode and its account before rendering the shell', () => {
  const account = {
    displayName: 'Ana',
    email: 'ana@example.com',
    appearance: 'light',
  }
  routing.pathname = '/'
  routing.matches = [{ context: { mode: 'authenticated', account } }]

  const { result } = renderHook(useRootLayout)

  expect(result.current.isPublic).toBe(false)
  expect(result.current.account).toEqual(account)
  expect(result.current.theme).toBe('light')
})

it('captures only recognized Learning identifiers and ignores run and foreign route state', () => {
  const id = '01J7T8AC91Z5K8M4JQ8C2D6F0B'
  routing.pathname = '/learning/goals/goal/skills/skill'
  routing.matches = [
    { context: null },
    {
      context: { displayName: 'Ana', email: 'ana@example.com' },
      params: {
        goalId: id,
        skillId: id,
        competencyId: id,
        materialId: id,
        activityId: id,
        runId: 'diagnostic',
      },
    },
  ]
  const { result, rerender } = renderHook(useRootLayout)
  expect(result.current.account?.email).toBe('ana@example.com')
  expect(result.current.mentorContextHint).toEqual({
    goalId: id,
    skillId: id,
    competencyId: id,
    materialId: id,
    activityId: id,
  })
  routing.matches = [{ context: {}, params: { goalId: id, skillId: 'invalid' } }]
  rerender()
  expect(result.current.mentorContextHint?.skillId).toBeNull()
  expect(result.current.account).toBeUndefined()
  routing.matches = [{ context: null, params: { goalId: 'invalid' } }]
  rerender()
  expect(result.current.mentorContextHint).toBeNull()
  routing.pathname = '/gamification'
  rerender()
  expect(result.current.mentorContextHint).toBeNull()
  routing.pathname = '/login/'
  rerender()
  expect(result.current.isPublic).toBe(true)
})

describe('useRootLayout theme', () => {
  const account = { displayName: 'Ana', email: 'ana@example.com' }

  it.each(['dark', 'light', 'system'] as const)(
    'uses the account %s appearance on protected routes',
    (appearance) => {
      routing.pathname = '/account/profile'
      routing.matches = [{ context: null }, { context: { ...account, appearance } }]
      const { result } = renderHook(useRootLayout)
      expect(result.current.theme).toBe(appearance)
    },
  )

  it.each([
    ['no account context', [{ context: null }]],
    ['an account without appearance', [{ context: account }]],
    ['an unknown appearance', [{ context: { ...account, appearance: 'sepia' } }]],
  ])('falls back to system on protected routes with %s', (_case, matches) => {
    routing.pathname = '/'
    routing.matches = matches
    const { result } = renderHook(useRootLayout)
    expect(result.current.theme).toBe('system')
  })

  it.each([
    '/login',
    '/register',
    '/forgot-password',
    '/reset-password',
    '/pending-confirmation',
    '/confirm-email',
    '/privacy',
  ])('keeps %s dark whatever the account appearance', (pathname) => {
    routing.pathname = pathname
    routing.matches = [{ context: { ...account, appearance: 'light' } }]
    const { result } = renderHook(useRootLayout)
    expect(result.current.theme).toBe('dark')
  })
})
