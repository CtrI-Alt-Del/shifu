import type { CookieSessionAuthProvider } from '@/provision/auth/cookie-session-auth-provider'

export type AuthContextValue = ReturnType<typeof CookieSessionAuthProvider>
