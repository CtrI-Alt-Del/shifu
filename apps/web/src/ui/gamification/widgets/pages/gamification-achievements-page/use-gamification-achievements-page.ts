import { useEffect } from 'react'

import { AuthError } from '@/core/errors/auth-error'
import type { Achievement, AchievementFamily } from '@/core/gamification/achievement'
import { useNavigation } from '@/ui/shared/hooks/use-navigation'

import { useAchievementsQuery } from './use-achievements-query'

export type GamificationAchievementsPageState = 'loading' | 'success' | 'empty' | 'error'

export type AchievementFamilyGroup = {
  family: AchievementFamily
  achievements: Achievement[]
  obtainedCount: number
}

export type AchievementsProgress = {
  obtainedCount: number
  catalogCount: number
}

const FAMILY_ORDER: AchievementFamily[] = [
  'diagnosis',
  'mastery',
  'completion',
  'streak',
  'level',
]

export function useGamificationAchievementsPage() {
  const { navigateTo } = useNavigation()
  const {
    overview,
    overviewError,
    isLoadingOverview,
    isFetchingOverview,
    refetchOverview,
  } = useAchievementsQuery()
  const isSessionRejected = overviewError instanceof AuthError
  const state: GamificationAchievementsPageState = isLoadingOverview
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
    achievementsProgress:
      state === 'success' && overview ? countProgress(overview.achievements) : null,
    state,
    isRetrying: isFetchingOverview && !isLoadingOverview,
    handleRetry,
  }
}

export type GamificationAchievementsPageController = ReturnType<
  typeof useGamificationAchievementsPage
>

function groupByFamily(achievements: Achievement[]): AchievementFamilyGroup[] {
  // A historical achievement still carries a resolved family, but it belongs
  // only in the dedicated historical section, not duplicated into a family
  // group.
  const current = achievements.filter((achievement) => achievement.state !== 'historical')
  return FAMILY_ORDER.map((family) => {
    const familyAchievements = current.filter(
      (achievement) => achievement.family === family,
    )
    return {
      family,
      achievements: familyAchievements,
      obtainedCount: familyAchievements.filter(
        (achievement) => achievement.state === 'obtained',
      ).length,
    }
  }).filter((group) => group.achievements.length > 0)
}

// Retired (historical) achievements are not part of the active catalog, so
// they count toward neither side of "X de Y obtidas".
function countProgress(achievements: Achievement[]): AchievementsProgress {
  const current = achievements.filter((achievement) => achievement.state !== 'historical')
  return {
    obtainedCount: current.filter((achievement) => achievement.state === 'obtained')
      .length,
    catalogCount: current.length,
  }
}
