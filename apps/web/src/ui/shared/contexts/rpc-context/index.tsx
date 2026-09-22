import { createContext, type PropsWithChildren } from 'react'

import type { RpcContextValue } from './types'
import { useRpcContextProvider } from './use-rpc-context-provider'

export type RpcContextProviderProps = PropsWithChildren

export const RpcContext = createContext<RpcContextValue | null>(null)

export const RpcContextProvider = ({ children }: RpcContextProviderProps) => {
  const value = useRpcContextProvider()

  return <RpcContext.Provider value={value}>{children}</RpcContext.Provider>
}
