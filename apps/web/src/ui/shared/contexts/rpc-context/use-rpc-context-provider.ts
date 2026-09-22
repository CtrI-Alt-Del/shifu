import { useMemo } from 'react'

import { LearningRpcService } from '@/rpc/services/learning-service'

import type { RpcContextValue } from './types'

export function useRpcContextProvider(): RpcContextValue {
  return useMemo(() => ({ learningService: LearningRpcService() }), [])
}
