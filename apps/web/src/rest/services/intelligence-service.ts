import { AppError } from '@/core/errors/app-error'
import type { RestClient } from '@/core/shared/interfaces/rest-client'

export type PlanningSessionItem = {
  created_at: string
  id: string
}

export type IntelligenceService = ReturnType<typeof IntelligenceService>

export const IntelligenceService = (restClient: RestClient) => {
  function validateStartPlanningResponse(body: unknown): PlanningSessionItem {
    if (
      !isRecord(body) ||
      typeof body.id !== 'string' ||
      typeof body.created_at !== 'string'
    ) {
      throw new AppError('A resposta do planejamento é inválida.', 'Erro de comunicação')
    }

    return body as unknown as PlanningSessionItem
  }

  return {
    async startPlanning(accessToken: string, initialIntent: string) {
      const response = await restClient.post<PlanningSessionItem>(
        '/intelligence/planning-sessions',
        { initial_intent: initialIntent },
        { headers: { Authorization: `Bearer ${accessToken}` } },
      )

      if (response.isFailure) response.throwError()
      return validateStartPlanningResponse(response.body)
    },
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}
