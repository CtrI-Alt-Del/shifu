export type ActivityXpRewardState = 'pending' | 'granted' | 'no-additional'

export type ActivityXpReward = {
  activityId: string
  attemptId: string
  state: ActivityXpRewardState
  additionalXp: number
  grantedXp: number
  maximumXp: number | null
}
