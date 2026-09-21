import { renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { CookieSessionAuthProvider } from '@/provision/auth/cookie-session-auth-provider'

import { useAuthContext } from '../use-auth-context'
import { useAuthContextProvider } from '../use-auth-context-provider'

vi.mock('@/provision/auth/cookie-session-auth-provider', () => ({
  CookieSessionAuthProvider: vi.fn(),
}))

const providerMock = vi.mocked(CookieSessionAuthProvider)
const providerValue = {
  signIn: vi.fn(),
}

describe('useAuthContextProvider', () => {
  beforeEach(() => {
    providerMock.mockReset()
    providerMock.mockReturnValue(providerValue)
  })

  it('composes the browser-safe auth surface once and preserves its identity', () => {
    const { result, rerender } = renderHook(() => useAuthContextProvider())

    expect(result.current).toBe(providerValue)
    rerender()

    expect(result.current).toBe(providerValue)
    expect(providerMock).toHaveBeenCalledTimes(1)
  })

  it('fails clearly when the consuming hook is outside its provider', () => {
    expect(() => renderHook(() => useAuthContext())).toThrow(
      'useAuthContext deve ser usado dentro de AuthContextProvider.',
    )
  })
})
