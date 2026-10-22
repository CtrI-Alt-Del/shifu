import type { AchievementsOverview } from '@/core/gamification/achievements-overview'
import type { GamificationOverview } from '@/core/gamification/overview'
import type { PracticeCalendar } from '@/core/gamification/practice-calendar'
import type { XpHistory } from '@/core/gamification/xp-history'
import type { RestClient } from '@/core/shared/interfaces/rest-client'

export type GamificationService = ReturnType<typeof GamificationService>

export const GamificationService = (restClient: RestClient) => {
  return {
    async getOverview(accessToken: string): Promise<GamificationOverview> {
      const response = await restClient.get<GamificationOverview>(
        '/gamification/overview',
        { headers: { Authorization: `Bearer ${accessToken}` } },
      )
      if (response.isFailure) response.throwError()
      return response.body
    },

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

    async getXpHistory(accessToken: string): Promise<XpHistory> {
      const response = await restClient.get<XpHistory>('/gamification/xp-history', {
        headers: { Authorization: `Bearer ${accessToken}` },
      })
      if (response.isFailure) response.throwError()
      return response.body
    },
  }
}
