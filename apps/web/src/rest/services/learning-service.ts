import type { CompetencyDetail } from '@/core/learning/competency-detail'
import type { GoalSummary } from '@/core/learning/goal-summary'
import type { RestClient } from '@/core/shared/interfaces/rest-client'

export type LearningService = ReturnType<typeof LearningService>

export const LearningService = (restClient: RestClient) => {
  return {
    async getGoals(accessToken: string): Promise<GoalSummary[]> {
      const response = await restClient.get<{ goals: GoalSummary[] }>('/learning/goals', {
        headers: { Authorization: `Bearer ${accessToken}` },
      })

      if (response.isFailure) response.throwError()
      return response.body.goals
    },

    async getCompetencyDetail(
      accessToken: string,
      goalId: string,
      skillId: string,
      competencyId: string,
    ): Promise<CompetencyDetail> {
      const response = await restClient.get<CompetencyDetail>(
        `/learning/goals/${goalId}/skills/${skillId}/competencies/${competencyId}`,
        { headers: { Authorization: `Bearer ${accessToken}` } },
      )

      if (response.isFailure) response.throwError()

      return response.body
    },
  }
}
