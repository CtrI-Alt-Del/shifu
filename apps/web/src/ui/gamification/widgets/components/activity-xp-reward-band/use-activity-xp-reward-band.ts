import { useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'

import { STREAK_REMINDER_QUERY_KEY } from '@/ui/gamification/constants/streak-reminder-query-keys'

import {
  MAX_POLL_ATTEMPTS,
  useActivityXpRewardQuery,
} from './use-activity-xp-reward-query'

export type ActivityXpRewardBandState =
  | { status: 'pending' }
  | { status: 'granted'; additionalXp: number; grantedXp: number; maximumXp: number }
  | { status: 'no-additional'; grantedXp: number; maximumXp: number | null }
  | { status: 'unavailable' }

export function useActivityXpRewardBand(
  activityId: string,
  attemptId: string,
): ActivityXpRewardBandState {
  const queryClient = useQueryClient()
  const { reward, rewardError, isLoadingReward, pollAttempts } = useActivityXpRewardQuery(
    activityId,
    attemptId,
  )
  const state = resolveState({ reward, rewardError, isLoadingReward, pollAttempts })
  const previousStatusRef = useRef<ActivityXpRewardBandState['status'] | null>(null)

  useEffect(() => {
    const previousStatus = previousStatusRef.current
    previousStatusRef.current = state.status
    // The first practice day may have just been recognized, so the reminder invite
    // state is read again once the reward leaves pending.
    if (previousStatus === 'pending' && state.status !== 'pending')
      void queryClient.invalidateQueries({ queryKey: STREAK_REMINDER_QUERY_KEY })
  }, [state.status, queryClient])

  return state
}

function resolveState({
  reward,
  rewardError,
  isLoadingReward,
  pollAttempts,
}: ReturnType<typeof useActivityXpRewardQuery>): ActivityXpRewardBandState {
  if (rewardError) return { status: 'unavailable' }
  if (isLoadingReward || !reward) return { status: 'pending' }

  if (reward.state === 'pending') {
    return pollAttempts >= MAX_POLL_ATTEMPTS
      ? { status: 'unavailable' }
      : { status: 'pending' }
  }

  if (reward.state === 'granted') {
    return {
      status: 'granted',
      additionalXp: reward.additionalXp,
      grantedXp: reward.grantedXp,
      maximumXp: reward.maximumXp ?? reward.grantedXp,
    }
  }

  return {
    status: 'no-additional',
    grantedXp: reward.grantedXp,
    maximumXp: reward.maximumXp,
  }
}
