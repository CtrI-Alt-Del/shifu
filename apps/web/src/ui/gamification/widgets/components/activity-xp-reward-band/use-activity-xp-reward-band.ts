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
  const { reward, rewardError, isLoadingReward, pollAttempts } = useActivityXpRewardQuery(
    activityId,
    attemptId,
  )

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
