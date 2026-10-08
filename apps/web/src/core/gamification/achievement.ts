// Matches the server's AchievementFamily StrEnum `.value` exactly
// (apps/server/.../gamification/core/domain/enums/achievement_family.py),
// which FastAPI serializes verbatim — lowercase, not the Python member name.
export type AchievementFamily =
  | 'diagnostico'
  | 'dominio'
  | 'conclusao'
  | 'sequencia'
  | 'nivel'

export type AchievementState = 'obtained' | 'locked' | 'historical'

// `family`/`name`/`description`/`criterionLabel`/`xpReward` are null for a
// `historical` achievement: its code was removed from the server's catalog,
// so that metadata no longer exists anywhere to serve (server-side:
// `ListAchievementsUseCase._historical_view`). Only `code`, `state` and
// `unlockedAt` are guaranteed for every achievement.
export type Achievement = {
  code: string
  family: AchievementFamily | null
  name: string | null
  description: string | null
  criterionLabel: string | null
  xpReward: number | null
  state: AchievementState
  unlockedAt: string | null
  progressCurrent: number | null
  progressTarget: number | null
}
