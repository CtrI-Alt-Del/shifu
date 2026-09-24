import { useId } from 'react'
import { useQuery } from '@tanstack/react-query'

import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import { getGoalDetail } from '@/provision/learning/get-goal-detail'

export function useGoalDetailQuery(goalId: string) {
  const instanceScope = useId()
  const query = useQuery({
    queryKey: ['learning', 'goal-detail', goalId, instanceScope],
    gcTime: 0,
    staleTime: 0,
    retry: false,
    queryFn: async () => {
      const result = await getGoalDetail({ data: { goalId } })

      if (result.kind === 'success') return result.detail
      if (result.kind === 'unauthorized' || result.kind === 'forbidden') {
        throw new AuthError('authentication-rejected', 'Sua sessão expirou.', {
          statusCode: result.statusCode,
        })
      }
      if (result.kind === 'not-found' || result.kind === 'invalid-request') {
        throw new RestError('Objetivo não encontrado.', 404)
      }
      throw new RestError(
        'Serviço temporariamente indisponível.',
        result.statusCode ?? 503,
      )
    },
  })

  return {
    goalDetail: query.data ?? null,
    goalDetailError: query.error ?? null,
    isLoadingGoalDetail: query.isPending,
    isFetchingGoalDetail: query.isFetching,
    refetchGoalDetail: query.refetch,
  }
}
