import { AppError } from '@/core/errors/app-error'
import type { RestClient } from '@/core/shared/interfaces/rest-client'

export type LearningGoalItem = {
  description: string
  id: string
  skill_count: number
  title: string
  updated_at: string
}

export type LearningService = ReturnType<typeof LearningService>

export const LearningService = (restClient: RestClient) => {
  function validateGoalsResponse(body: unknown): LearningGoalItem[] {
    if (!isRecord(body) || !Array.isArray(body.goals)) {
      throw new AppError('A resposta de Objetivos é inválida.', 'Erro de comunicação')
    }

    return body.goals as LearningGoalItem[]
  }

  return {
    async getGoals(accessToken: string) {
      const response = await restClient.get<{ goals: LearningGoalItem[] }>(
        '/learning/goals',
        { headers: { Authorization: `Bearer ${accessToken}` } },
      )

      if (response.isFailure) response.throwError()
      return validateGoalsResponse(response.body)
    },
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}
