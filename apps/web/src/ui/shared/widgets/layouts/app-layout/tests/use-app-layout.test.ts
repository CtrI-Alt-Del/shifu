import { describe, expect, it } from 'vitest'

import { ROUTES } from '@/constants/routes'

import {
  APP_NAVIGATION_ITEMS,
  isNavigationItemActive,
  type NavigationItem,
} from '../use-app-layout'

const GOALS_ITEM = APP_NAVIGATION_ITEMS[0]
const PROGRESS_ITEM = APP_NAVIGATION_ITEMS[1]
const MENTOR_ITEM = APP_NAVIGATION_ITEMS[2]
const ACCOUNT_ITEM: NavigationItem = { label: 'Conta', route: 'account' }

function activeLabelsOf(pathname: string): string[] {
  return [...APP_NAVIGATION_ITEMS, ACCOUNT_ITEM]
    .filter((item) => isNavigationItemActive(pathname, item))
    .map((item) => item.label)
}

describe('useAppLayout', () => {
  it('returns the three shared destinations in their product order', () => {
    expect(APP_NAVIGATION_ITEMS).toEqual([
      { label: 'Objetivos', route: 'root', activeRoutes: ['learning'] },
      { label: 'Progresso', route: 'gamification' },
      { label: 'Mentor', route: 'intelligence' },
    ])
  })

  it('keeps a nested destination active and normalizes trailing slashes', () => {
    expect(isNavigationItemActive('/gamification/', PROGRESS_ITEM)).toBe(true)
    expect(isNavigationItemActive('/gamification/history', PROGRESS_ITEM)).toBe(true)
    expect(isNavigationItemActive('/intelligence/chat', MENTOR_ITEM)).toBe(true)
  })

  it('keeps the home destination exact-only for its own route', () => {
    expect(isNavigationItemActive(ROUTES.root, GOALS_ITEM)).toBe(true)
    expect(isNavigationItemActive('/objectives/details', GOALS_ITEM)).toBe(false)
    expect(isNavigationItemActive(ROUTES.gamification, GOALS_ITEM)).toBe(false)
  })

  it('activates Objetivos on the learning area and every nested learning path', () => {
    expect(isNavigationItemActive(ROUTES.learning, GOALS_ITEM)).toBe(true)
    expect(isNavigationItemActive(`${ROUTES.learning}/`, GOALS_ITEM)).toBe(true)
    expect(isNavigationItemActive('/learning/goals/x', GOALS_ITEM)).toBe(true)
    expect(isNavigationItemActive('/learning/goals/x/skills/y', GOALS_ITEM)).toBe(true)
  })

  it('does not activate Objetivos for look-alike or unrelated paths', () => {
    expect(isNavigationItemActive('/learningx', GOALS_ITEM)).toBe(false)
    expect(isNavigationItemActive(ROUTES.gamification, GOALS_ITEM)).toBe(false)
    expect(isNavigationItemActive(ROUTES.intelligence, GOALS_ITEM)).toBe(false)
    expect(isNavigationItemActive(ROUTES.account, GOALS_ITEM)).toBe(false)
  })

  it('marks only Objetivos active on the home and learning paths', () => {
    expect(activeLabelsOf(ROUTES.root)).toEqual(['Objetivos'])
    expect(activeLabelsOf(ROUTES.learning)).toEqual(['Objetivos'])
    expect(activeLabelsOf('/learning/goals/x')).toEqual(['Objetivos'])
  })

  it('keeps the other areas on their own active item', () => {
    expect(activeLabelsOf(ROUTES.gamification)).toEqual(['Progresso'])
    expect(activeLabelsOf(ROUTES.intelligence)).toEqual(['Mentor'])
    expect(activeLabelsOf(ROUTES.account)).toEqual(['Conta'])
    expect(activeLabelsOf('/learningx')).toEqual([])
  })

  it('treats an item without extra routes as matching only its own route', () => {
    expect(isNavigationItemActive('/learning/goals/x', ACCOUNT_ITEM)).toBe(false)
    expect(isNavigationItemActive('/account/profile', ACCOUNT_ITEM)).toBe(true)
  })
})
