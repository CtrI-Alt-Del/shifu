import type { RequestTelemetryContext } from '@/core/shared/interfaces/request-telemetry-context'
import type { GoalDetail } from '@/core/learning/goal-detail'
import { createServerRequestClient } from '@/rest/axios/server-request-client'
import { LearningService } from '@/rest/services/learning-service'
import { BetterAuthConfig } from '@/provision/auth/better-auth/better-auth-config'

export type GoalDetailProvider = ReturnType<typeof GoalDetailProvider>

export const GoalDetailProvider = (context?: RequestTelemetryContext) => {
  const learningService = LearningService(
    createServerRequestClient(context, { baseUrl: BetterAuthConfig().identityURL }),
  )

  return {
    getGoalDetail(accessToken: string, goalId: string): Promise<GoalDetail> {
      return learningService.getGoalDetail(accessToken, goalId)
    },
  }
}
