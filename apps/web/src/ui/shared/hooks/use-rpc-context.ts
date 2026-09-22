import { useContext } from 'react'

import { AppError } from '@/core/errors/app-error'
import { RpcContext } from '@/ui/shared/contexts/rpc-context'

export function useRpcContext() {
  const context = useContext(RpcContext)

  if (!context) {
    throw new AppError('useRpcContext deve ser usado dentro de RpcContextProvider.')
  }

  return context
}
