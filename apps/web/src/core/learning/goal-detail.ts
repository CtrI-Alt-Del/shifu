import type { SkillRecommendation } from './skill-experience'
import type { ActivityAnswer } from './choice-activity'

export type DiagnosticSubmissionItem = {
  competencyId: string
  activityId: string
  activityRevision: string
  answers: ActivityAnswer[]
}

export const GOAL_DETAIL_ID_PATTERN = /^[A-Z0-9]{26}$/

export type AvailableSkill = {
  id: string
  name: string
  available: boolean
  unavailableReason: string | null
}

export type SkillExperienceStatus =
  | 'not-started'
  | 'diagnosing'
  | 'learning'
  | 'completed'

export type GoalSkillDetail = {
  skillExperienceId: string
  skillId: string
  name: string
  skillName?: string
  status: SkillExperienceStatus
  progress: number | null
  inclusionReason: string | null
}

export type GoalSkill = GoalSkillDetail

export type GoalSkillRelation = {
  foundationSkillId: string
  skillId: string
}

export type GoalDetail = {
  goalId: string
  title: string
  description: string
  skills: readonly GoalSkillDetail[]
  relations: readonly GoalSkillRelation[]
}

export type DiagnosticCompetency = {
  competencyId: string
  competencyName: string
  position: number
  progress: number | null
  coverageComplete: boolean
  status: 'learning' | 'developing' | 'proficient' | 'mastered' | null
  isFocus: boolean
  contentReleased: boolean
}

export type DiagnosticOverview = {
  status: GoalSkill['status']
  runState: 'requires_entry' | 'active' | 'ready_to_complete' | 'settled'
  readyToComplete: boolean
  nextCompetencyId: string | null
  nextActivityId: string | null
  pendingAttemptId: string | null
  pendingAttemptStatus: 'pending' | 'failed' | null
  activitySequence?: { competencyId: string; activityId: string }[]
  focusCompetencyId: string | null
  competencies: DiagnosticCompetency[]
  initialRecommendation?: SkillRecommendation | null
  initialRecommendationGap?: string | null
  initialOverallResult: number | null
  overallCoverageComplete: boolean
  directCompletion: boolean
}
