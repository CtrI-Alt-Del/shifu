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
  policyId?: string | null
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
  progress: number | null
}

export type DiagnosticOverview = {
  status: GoalSkill['status']
  nextCompetencyId: string | null
  nextActivityId: string | null
  pendingAttemptId: string | null
  pendingAttemptStatus: 'pending' | 'failed' | null
  focusCompetencyId: string | null
  competencies: DiagnosticCompetency[]
}
