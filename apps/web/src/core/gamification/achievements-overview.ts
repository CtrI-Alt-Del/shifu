import type { Achievement } from '@/core/gamification/achievement'

export type AchievementsOverview = {
  level: number
  totalXp: number
  xpForNextLevel: number
  achievements: Achievement[]
}
