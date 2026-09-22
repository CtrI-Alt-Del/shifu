import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'

import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import { useNavigation } from '@/ui/shared/hooks/use-navigation'
import { useRpcContext } from '@/ui/shared/hooks/use-rpc-context'

export type CompetencyDetailPageProps = {
  goalId: string
  skillId: string
  competencyId: string
}

export function useCompetencyDetailPage({
  competencyId,
  goalId,
  skillId,
}: CompetencyDetailPageProps) {
  const { learningService } = useRpcContext()
  const { navigateTo } = useNavigation()
  const query = useQuery({
    queryKey: ['learning', 'competency-detail', goalId, skillId, competencyId],
    queryFn: () => learningService.getCompetencyDetail(goalId, skillId, competencyId),
    refetchOnWindowFocus: false,
    retry: (failureCount, error) =>
      error instanceof RestError && error.statusCode === 429 && failureCount < 2,
    retryDelay: (_failureCount, error) => (error instanceof RestError ? 1000 : 0),
  })

  const isPrivateAbsence =
    query.error instanceof RestError && query.error.statusCode === 404
  const isSessionRejected = query.error instanceof AuthError

  useEffect(() => {
    if (!isSessionRejected) return

    void navigateTo('login')
  }, [isSessionRejected, navigateTo])

  return {
    detail: query.data ?? null,
    error: query.error ?? null,
    handleRetry: query.refetch,
    isLoading: query.isPending,
    isPrivateAbsence,
    isRecoverableError: Boolean(query.error) && !isPrivateAbsence && !isSessionRejected,
  }
}

export type CompetencyDetailPageController = ReturnType<typeof useCompetencyDetailPage>
