// Matches the server's AchievementFamily StrEnum `.value` exactly
// (apps/server/.../gamification/core/domain/enums/achievement_family.py),
// which FastAPI serializes verbatim — lowercase, not the Python member name.
export type AchievementFamily =
  | 'diagnosis'
  | 'mastery'
  | 'completion'
  | 'streak'
  | 'level'

export type AchievementState = 'obtained' | 'locked' | 'historical'

// A `historical` achievement (its code retired from the catalog) still
// carries name/description/criterion/xpReward: `EarnedAchievement` snapshots
// them at unlock time (server-side: `ListAchievementsUseCase`). Only
// `unlockedAt`/`progressCurrent`/`progressTarget` are state-dependent.
export type Achievement = {
  code: string
  family: AchievementFamily
  name: string
  description: string
  criterionLabel: string
  xpReward: number
  state: AchievementState
  unlockedAt: string | null
  progressCurrent: number | null
  progressTarget: number | null
}
