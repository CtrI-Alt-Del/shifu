import { useQuery } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'

import { SERVER_ENV } from '@/constants/server-env'
import { AppError } from '@/core/errors/app-error'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { AxiosRestClient } from '@/rest/axios/axios-rest-client'
import { LearningService, type LearningGoalItem } from '@/rest/services/learning-service'

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

export type GoalSummary = {
  description: string
  id: string
  skillCount: number
  title: string
  updatedAt: string
}

export function useHomeGoalsQuery() {
  const {
    data: goals = [],
    error: goalsError,
    isLoading: isLoadingGoals,
    refetch: refetchGoals,
  } = useQuery({
    queryFn: async () => {
      const items = await fetchHomeGoals()
      return items.map(mapGoalSummary)
    },
    queryKey: ['learning', 'home-goals'],
  })

  return { goals, goalsError, isLoadingGoals, refetchGoals }
}

function mapGoalSummary(item: LearningGoalItem): GoalSummary {
  return {
    description: item.description,
    id: item.id,
    skillCount: item.skill_count,
    title: item.title,
    updatedAt: item.updated_at,
  }
}
