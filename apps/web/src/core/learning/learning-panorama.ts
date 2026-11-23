import type { SkillExperienceStatus } from '@/core/learning/skill-experience'

export type StageDistribution = {
  notStarted: number
  diagnosing: number
  learning: number
  completed: number
  /** Objetivos that contain at least one experience; never a per-Objetivo value. */
  goalCount: number
}

export type ResumeItem = {
  skillExperienceId: string
  goalId: string
  goalTitle: string
  skillId: string
  skillName: string
  status: Extract<SkillExperienceStatus, 'diagnosing' | 'learning'>
  /** Present for the learning stage only. */
  focusCompetencyName: string | null
  lastSubmittedAt: string | null
}

export type WeeklyCount = {
  /** Local Monday, `YYYY-MM-DD`. */
  weekStart: string
  count: number
}

export type EvolutionOption = {
  skillExperienceId: string
  goalTitle: string
  skillName: string
  status: Exclude<SkillExperienceStatus, 'not-started'>
}

export type CompletedSkill = {
  skillExperienceId: string
  goalId: string
  goalTitle: string
  skillId: string
  skillName: string
  finalResult: number | null
  /** Local date, `YYYY-MM-DD`. */
  completedOn: string
}

export type RecentMastery = {
  skillExperienceId: string
  goalId: string
  goalTitle: string
  skillId: string
  skillName: string
  competencyId: string
  competencyName: string
  /** Local date, `YYYY-MM-DD`. */
  masteredOn: string
}

export type LearningPanorama = {
  hasGoals: boolean
  completedSkillCount: number
  masteredCompetencyCount: number
  stageDistribution: StageDistribution
  /** At most three. */
  resumeItems: ResumeItem[]
  /** Exactly eight local weeks, oldest first. */
  weeklyEvaluatedActivities: WeeklyCount[]
  evolutionOptions: EvolutionOption[]
  defaultEvolutionSkillExperienceId: string | null
  /** Newest completion first. */
  completedSkills: CompletedSkill[]
  /** At most five, newest first. */
  recentMasteries: RecentMastery[]
}
