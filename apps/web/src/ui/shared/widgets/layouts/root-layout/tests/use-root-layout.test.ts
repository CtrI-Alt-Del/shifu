import { describe, expect, it } from 'vitest'

import { isPublicRoute } from '../use-root-layout'

describe('useRootLayout route classification', () => {
  it('classifies every public contract path without treating protected paths as public', () => {
    expect(isPublicRoute('/login/')).toBe(true)
    expect(isPublicRoute('/register')).toBe(true)
    expect(isPublicRoute('/forgot-password/')).toBe(true)
    expect(isPublicRoute('/pending-confirmation')).toBe(true)
    expect(isPublicRoute('/confirm-email')).toBe(true)
    expect(isPublicRoute('/account')).toBe(false)
    expect(isPublicRoute('/')).toBe(false)
  })
})
