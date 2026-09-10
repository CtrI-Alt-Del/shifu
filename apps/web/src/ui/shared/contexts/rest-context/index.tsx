import { createContext, type PropsWithChildren } from 'react'

import type { RestContextValue } from './types'
import { useRestContextProvider } from './use-rest-context-provider'

export type RestContextProviderProps = PropsWithChildren

export const RestContext = createContext<RestContextValue | null>(null)

export const RestContextProvider = ({ children }: RestContextProviderProps) => {
  const value = useRestContextProvider()

  return <RestContext.Provider value={value}>{children}</RestContext.Provider>
}
