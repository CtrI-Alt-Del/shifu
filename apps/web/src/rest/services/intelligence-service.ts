import type { RestClient } from '@/core/shared/interfaces/rest-client'

export type PlanningSessionItem = {
  created_at: string
  id: string
}

export type IntelligenceService = ReturnType<typeof IntelligenceService>

export const IntelligenceService = (restClient: RestClient) => {
  return {
    async startPlanning(
      accessToken: string,
      initialIntent: string,
    ): Promise<PlanningSessionItem> {
      const response = await restClient.post<PlanningSessionItem>(
        '/intelligence/planning-sessions',
        { initial_intent: initialIntent },
        { headers: { Authorization: `Bearer ${accessToken}` } },
      )

      if (response.isFailure) response.throwError()
      return response.body
    },
  }
}
