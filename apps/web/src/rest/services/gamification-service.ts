import type { AchievementsOverview } from '@/core/gamification/achievements-overview'
import type { PracticeCalendar } from '@/core/gamification/practice-calendar'
import type { RestClient } from '@/core/shared/interfaces/rest-client'

export type GamificationService = ReturnType<typeof GamificationService>

export const GamificationService = (restClient: RestClient) => {
  return {
    async listAchievements(accessToken: string): Promise<AchievementsOverview> {
      const response = await restClient.get<AchievementsOverview>(
        '/gamification/achievements',
        { headers: { Authorization: `Bearer ${accessToken}` } },
      )
      if (response.isFailure) response.throwError()
      return response.body
    },

    async getPracticeCalendar(
      accessToken: string,
      year: number,
      month: number,
    ): Promise<PracticeCalendar> {
      const response = await restClient.get<PracticeCalendar>(
        `/gamification/calendar?year=${year}&month=${month}`,
        { headers: { Authorization: `Bearer ${accessToken}` } },
      )
      if (response.isFailure) response.throwError()
      return response.body
    },
  }
}
