import type { GamificationOverview } from '@/core/gamification/overview'

import { useOverviewQuery } from './use-overview-query'

export type OverviewTabPanelState = 'loading' | 'success' | 'empty' | 'error'

// "No reward at all" is the union of the three blocks being empty, not just
// an absent profile: a learner whose profile exists but who has never
// practised reads the same initial state (CA-22).
function hasNoReward(overview: GamificationOverview): boolean {
  return (
    overview.totalXp === 0 &&
    overview.streak.streak.longest === 0 &&
    overview.achievements.recent.length === 0
  )
}

export function useOverviewTabPanel() {
  const {
    overview,
    overviewError,
    isLoadingOverview,
    isFetchingOverview,
    refetchOverview,
  } = useOverviewQuery()

  const state: OverviewTabPanelState = isLoadingOverview
    ? 'loading'
    : overviewError || !overview
      ? 'error'
      : hasNoReward(overview)
        ? 'empty'
        : 'success'

  return {
    overview: state === 'success' ? overview : null,
    state,
    isRetrying: isFetchingOverview && !isLoadingOverview,
    handleRetry: () => void refetchOverview(),
  }
}

export type OverviewTabPanelController = ReturnType<typeof useOverviewTabPanel>
