import { createContext, type PropsWithChildren } from 'react'

import type { AuthContextValue } from './types'
import { useAuthContextProvider } from './use-auth-context-provider'

export type AuthContextProviderProps = PropsWithChildren

export const AuthContext = createContext<AuthContextValue | null>(null)

export const AuthContextProvider = ({ children }: AuthContextProviderProps) => {
  const value = useAuthContextProvider()

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
