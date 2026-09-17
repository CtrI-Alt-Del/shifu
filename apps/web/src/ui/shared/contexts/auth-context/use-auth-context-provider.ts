import { useMemo } from 'react'

import { CookieSessionAuthProvider } from '@/provision/auth/cookie-session-auth-provider'

import type { AuthContextValue } from './types'

export function useAuthContextProvider(): AuthContextValue {
  return useMemo(() => CookieSessionAuthProvider(), [])
}
