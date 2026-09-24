export const GOAL_DETAIL_ID_PATTERN = /^[A-Z0-9]{26}$/

export type SkillExperienceStatus =
  | 'not-started'
  | 'diagnosing'
  | 'learning'
  | 'completed'

export type GoalSkillDetail = {
  skillExperienceId: string
  skillId: string
  name: string
  status: SkillExperienceStatus
  progress: number | null
  inclusionReason: string | null
}

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
