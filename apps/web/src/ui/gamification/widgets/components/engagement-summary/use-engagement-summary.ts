import { useGamificationOverviewQuery } from '@/ui/gamification/hooks/use-gamification-overview-query'
import { useFormatXp } from '@/ui/shared/hooks/use-format-xp'

export type EngagementSummaryState = 'loading' | 'error' | 'success'

export type EngagementSummaryValues = {
  level: number
  totalXp: number
  xpForNextLevel: number
  levelPercentage: number
  currentStreak: number
  longestStreak: number
}

export function useEngagementSummary() {
  const {
    overview,
    overviewError,
    isLoadingOverview,
    isFetchingOverview,
    refetchOverview,
  } = useGamificationOverviewQuery()
  const { formatXp } = useFormatXp()

  const state: EngagementSummaryState = isLoadingOverview
    ? 'loading'
    : overviewError || !overview
      ? 'error'
      : 'success'

  const summary: EngagementSummaryValues | null =
    state === 'success' && overview
      ? {
          level: overview.level,
          totalXp: overview.totalXp,
          xpForNextLevel: overview.xpForNextLevel,
          levelPercentage: overview.levelPercentage,
          currentStreak: overview.streak.streak.current,
          longestStreak: overview.streak.streak.longest,
        }
      : null

  function handleRetry() {
    void refetchOverview()
  }

  return {
    summary,
    state,
    isRetrying: isFetchingOverview && !isLoadingOverview,
    formatXp,
    handleRetry,
  }
}
