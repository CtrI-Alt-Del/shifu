export type AvailableSkill = {
  id: string
  name: string
  available: boolean
  unavailableReason: string | null
}

export type GoalSkill = {
  skillId: string
  skillName: string
  status: 'not-started' | 'diagnosing' | 'learning' | 'completed'
  policyId: string | null
}

export type GoalDetail = {
  goalId: string
  title: string
  description: string
  skills: GoalSkill[]
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
