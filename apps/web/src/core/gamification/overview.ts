import type { CalendarDay, PracticeStreak } from '@/core/gamification/practice-calendar'

export type RecentAchievement = {
  achievementId: string
  name: string
  criterionLabel: string
  xpReward: number
  achievedAt: string
}

export type AchievementCriterionKind =
  | 'diagnostics_completed'
  | 'competencies_mastered'
  | 'skills_completed'
  | 'longest_streak'
  | 'level'

// The locked active achievement closest to its criterion. `progressCurrent`
// is already clamped to `progressTarget` by the server.
export type NextAchievement = {
  achievementId: string
  name: string
  criterionLabel: string
  criterionKind: AchievementCriterionKind
  xpReward: number
  progressCurrent: number
  progressTarget: number
}

export type AchievementsSummary = {
  recent: RecentAchievement[]
  obtainedCount: number
  catalogCount: number
  nextAchievement: NextAchievement | null
}

export type StreakOverview = {
  streak: PracticeStreak
  currentMonth: CalendarDay[]
  today: string
}

// One local week, Monday to Sunday; `weekStart` is the Monday as YYYY-MM-DD.
export type WeeklyXp = {
  weekStart: string
  xp: number
}

export type GamificationOverview = {
  level: number
  totalXp: number
  currentLevelXp: number
  nextLevelXp: number
  xpForNextLevel: number
  levelPercentage: number
  streak: StreakOverview
  achievements: AchievementsSummary
  weeklyXp: WeeklyXp[]
}
