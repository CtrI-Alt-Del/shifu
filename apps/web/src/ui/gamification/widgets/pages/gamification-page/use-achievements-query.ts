import { useQuery } from '@tanstack/react-query'

import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import { getAchievements } from '@/provision/gamification/get-achievements'

export function useAchievementsQuery() {
  const query = useQuery({
    queryKey: ['gamification', 'achievements'],
    retry: false,
    queryFn: async () => {
      const result = await getAchievements()

      if (result.kind === 'success') return result.overview
      if (result.kind === 'unauthorized' || result.kind === 'forbidden') {
        throw new AuthError('authentication-rejected', 'Sua sessão expirou.', {
          statusCode: result.statusCode,
        })
      }
      throw new RestError(
        'Serviço temporariamente indisponível.',
        result.statusCode ?? 503,
      )
    },
  })

  return {
    overview: query.data ?? null,
    overviewError: query.error ?? null,
    isLoadingOverview: query.isPending,
    isFetchingOverview: query.isFetching,
    refetchOverview: query.refetch,
  }
}
