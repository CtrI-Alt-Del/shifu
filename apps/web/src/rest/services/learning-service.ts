import type { CompetencyDetail } from '@/core/learning/competency-detail'
import type { GoalSummary } from '@/core/learning/goal-summary'
import type { CreatedSkillExperience } from '@/core/learning/created-skill-experience'
import type { GoalDetail } from '@/core/learning/goal-detail'
import type { SkillCatalogPage } from '@/core/learning/skill-catalog-page'

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

    async getGoalDetail(accessToken: string, goalId: string): Promise<GoalDetail> {
      const response = await restClient.get<GoalDetail>(`/learning/goals/${goalId}`, {
        headers: { Authorization: 'Bearer ' + accessToken },
      })

      if (response.isFailure) response.throwError()

      return response.body
    },

    async searchSkillCatalog(
      accessToken: string,
      goalId: string,
      params: { query?: string; cursor?: string; limit?: number },
    ): Promise<SkillCatalogPage> {
      const response = await restClient.get<SkillCatalogPage>(
        `/learning/goals/${goalId}/skills/catalog`,
        {
          params,
          headers: { Authorization: `Bearer ${accessToken}` },
        },
      )

      if (response.isFailure) response.throwError()

      return response.body
    },

    async addSkillToGoal(
      accessToken: string,
      goalId: string,
      skillId: string,
      foundationSkillIds: readonly string[],
    ): Promise<CreatedSkillExperience[]> {
      const response = await restClient.post<{ created: CreatedSkillExperience[] }>(
        `/learning/goals/${goalId}/skills`,
        { skill_id: skillId, foundation_skill_ids: foundationSkillIds },
        { headers: { Authorization: `Bearer ${accessToken}` } },
      )

      if (response.isFailure) response.throwError()

      return response.body.created
    },
  }
}
