import type { XpHistoryEntry } from '@/core/gamification/xp-history'

import { useXpHistoryQuery } from './use-xp-history-query'

export type GamificationXpHistoryPageState = 'loading' | 'success' | 'empty' | 'error'

export function useGamificationXpHistoryPage() {
  const { history, historyError, isLoadingHistory, isFetchingHistory, refetchHistory } =
    useXpHistoryQuery()

  const state: GamificationXpHistoryPageState = isLoadingHistory
    ? 'loading'
    : historyError || !history
      ? 'error'
      : history.entries.length === 0
        ? 'empty'
        : 'success'

  const entries: XpHistoryEntry[] = state === 'success' && history ? history.entries : []

  return {
    entries,
    totalXp: history?.totalXp ?? 0,
    state,
    isRetrying: isFetchingHistory && !isLoadingHistory,
    handleRetry: () => void refetchHistory(),
  }
}

export type GamificationXpHistoryPageController = ReturnType<
  typeof useGamificationXpHistoryPage
>
