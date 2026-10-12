import { useEffect } from 'react'

import { AuthError } from '@/core/errors/auth-error'
import type { Achievement, AchievementFamily } from '@/core/gamification/achievement'
import { useNavigation } from '@/ui/shared/hooks/use-navigation'

import { useAchievementsQuery } from './use-achievements-query'

export type GamificationPageState = 'loading' | 'success' | 'empty' | 'error'

export type AchievementFamilyGroup = {
  family: AchievementFamily
  achievements: Achievement[]
}

export type ProfileSummary = {
  level: number
  totalXp: number
  xpForNextLevel: number
}

const FAMILY_ORDER: AchievementFamily[] = [
  'diagnosis',
  'mastery',
  'completion',
  'streak',
  'level',
]

export function useGamificationPage() {
  const { navigateTo } = useNavigation()
  const {
    overview,
    overviewError,
    isLoadingOverview,
    isFetchingOverview,
    refetchOverview,
  } = useAchievementsQuery()
  const isSessionRejected = overviewError instanceof AuthError
  const state: GamificationPageState = isLoadingOverview
    ? 'loading'
    : overviewError || !overview
      ? 'error'
      : overview.achievements.length === 0
        ? 'empty'
        : 'success'

  useEffect(() => {
    if (isSessionRejected) void navigateTo('login')
  }, [isSessionRejected, navigateTo])

  function handleRetry() {
    void refetchOverview()
  }

  return {
    familyGroups:
      state === 'success' && overview ? groupByFamily(overview.achievements) : [],
    historicalAchievements:
      state === 'success' && overview
        ? overview.achievements.filter(
            (achievement) => achievement.state === 'historical',
          )
        : [],
    profileSummary:
      state === 'success' && overview
        ? {
            level: overview.level,
            totalXp: overview.totalXp,
            xpForNextLevel: overview.xpForNextLevel,
          }
        : null,
    state,
    isRetrying: isFetchingOverview && !isLoadingOverview,
    handleRetry,
  }
}

export type GamificationPageController = ReturnType<typeof useGamificationPage>

function groupByFamily(achievements: Achievement[]): AchievementFamilyGroup[] {
  // A historical achievement still carries a resolved family, but it belongs
  // only in the dedicated historical section, not duplicated into a family
  // group.
  const current = achievements.filter((achievement) => achievement.state !== 'historical')
  return FAMILY_ORDER.map((family) => ({
    family,
    achievements: current.filter((achievement) => achievement.family === family),
  })).filter((group) => group.achievements.length > 0)
}
