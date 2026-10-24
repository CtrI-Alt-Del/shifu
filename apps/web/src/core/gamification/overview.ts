import type { CalendarDay, PracticeStreak } from '@/core/gamification/practice-calendar'

export type RecentAchievement = {
  achievementId: string
  name: string
  criterionLabel: string
  xpReward: number
  achievedAt: string
}

export type AchievementsSummary = {
  recent: RecentAchievement[]
  obtainedCount: number
  catalogCount: number
}

export type StreakOverview = {
  streak: PracticeStreak
  lastSevenDays: CalendarDay[]
  today: string
  isTodayPending: boolean
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
}
