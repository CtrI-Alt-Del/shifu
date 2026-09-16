import { describe, expect, it } from 'vitest'

import { APP_NAVIGATION_ITEMS, isNavigationItemActive } from '../use-app-layout'

describe('useAppLayout', () => {
  it('returns the three shared destinations in their product order', () => {
    expect(APP_NAVIGATION_ITEMS).toEqual([
      { label: 'Objetivos', route: 'root' },
      { label: 'Progresso', route: 'gamification' },
      { label: 'Mentor', route: 'intelligence' },
    ])
  })

  it('keeps a nested destination active and normalizes trailing slashes', () => {
    expect(isNavigationItemActive('/gamification/', 'gamification')).toBe(true)
    expect(isNavigationItemActive('/gamification/history', 'gamification')).toBe(true)
    expect(isNavigationItemActive('/intelligence/chat', 'intelligence')).toBe(true)
  })

  it('keeps the home destination exact-only', () => {
    expect(isNavigationItemActive('/', 'root')).toBe(true)
    expect(isNavigationItemActive('/objectives/details', 'root')).toBe(false)
    expect(isNavigationItemActive('/gamification', 'root')).toBe(false)
  })
})
