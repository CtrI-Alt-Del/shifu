import { useQuery } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'

import { SERVER_ENV } from '@/constants/server-env'
import { AppError } from '@/core/errors/app-error'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { AxiosRestClient } from '@/rest/axios/axios-rest-client'
import { LearningService } from '@/rest/services/learning-service'

const fetchHomeGoals = createServerFn({ method: 'GET' }).handler(async () => {
  const access = await getBetterAuthProvider().getCurrentAccess(getRequest())
  if (!access) {
    throw new AppError('Sua sessão expirou. Atualize a página.', 'Erro de autenticação')
  }

  const learningService = LearningService(
    AxiosRestClient(SERVER_ENV.shifuServerAppUrl, { withCredentials: false }),
  )
  return learningService.getGoals(access.accessToken)
})

export function useHomeGoalsQuery() {
  const {
    data: goals = [],
    error: goalsError,
    isLoading: isLoadingGoals,
    refetch: refetchGoals,
  } = useQuery({
    retry: 1,
    queryFn: fetchHomeGoals,
    queryKey: ['learning', 'home-goals'],
  })

  return { goals, goalsError, isLoadingGoals, refetchGoals }
}
