import type { AchievementsOverview } from '@/core/gamification/achievements-overview'
import { AxiosRestClient } from '@/rest/axios/axios-rest-client'
import { GamificationService } from '@/rest/services/gamification-service'
import { BetterAuthConfig } from '@/provision/auth/better-auth/better-auth-config'

export type AchievementsProvider = ReturnType<typeof AchievementsProvider>

export const AchievementsProvider = () => {
  const gamificationService = GamificationService(
    AxiosRestClient(BetterAuthConfig().identityURL, { withCredentials: false }),
  )

  return {
    getAchievements(accessToken: string): Promise<AchievementsOverview> {
      return gamificationService.listAchievements(accessToken)
    },
  }
}
