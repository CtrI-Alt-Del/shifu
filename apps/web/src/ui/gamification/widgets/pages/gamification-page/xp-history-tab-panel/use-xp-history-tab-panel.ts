import type { XpHistoryEntry } from '@/core/gamification/xp-history'

import { useXpHistoryQuery } from './use-xp-history-query'

export type XpHistoryTabPanelState = 'loading' | 'success' | 'empty' | 'error'

export function useXpHistoryTabPanel() {
  const { history, historyError, isLoadingHistory, isFetchingHistory, refetchHistory } =
    useXpHistoryQuery()

  const state: XpHistoryTabPanelState = isLoadingHistory
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

export type XpHistoryTabPanelController = ReturnType<typeof useXpHistoryTabPanel>
