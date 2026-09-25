import type { GoalDetail } from '@/core/learning/goal-detail'
import { AxiosRestClient } from '@/rest/axios/axios-rest-client'
import { LearningService } from '@/rest/services/learning-service'
import { BetterAuthConfig } from '@/provision/auth/better-auth/better-auth-config'

export type GoalDetailProvider = ReturnType<typeof GoalDetailProvider>

export const GoalDetailProvider = () => {
  const learningService = LearningService(
    AxiosRestClient(BetterAuthConfig().identityURL, { withCredentials: false }),
  )

  return {
    getGoalDetail(accessToken: string, goalId: string): Promise<GoalDetail> {
      return learningService.getGoalDetail(accessToken, goalId)
    },
  }
}
