export type MentorActionKind = 'add_skill' | 'remove_skill'
export type MentorActionProposalStatus = 'pending' | 'declined' | 'completed' | 'rejected'
export type MentorActionProposalOutcome = 'added' | 'already_present' | 'removed'
export type MentorActionRejectionReason =
  | 'goal_unavailable'
  | 'skill_unavailable'
  | 'experience_unavailable'
export type MentorActionCandidateGoal = {
  goalId: string
  title: string
  containsSkill: boolean
  skillExperienceId: string | null
}
export type MentorActionProposal = {
  id: string
  sourceMessageId: string
  kind: MentorActionKind
  skillId: string
  skillName: string
  goalId: string | null
  goalTitle: string | null
  skillExperienceId: string | null
  candidateGoals: MentorActionCandidateGoal[]
  justification: string | null
  status: MentorActionProposalStatus
  outcome: MentorActionProposalOutcome | null
  rejectionReason: MentorActionRejectionReason | null
  resolvedGoalId: string | null
  resolvedSkillExperienceId: string | null
  createdAt: string
}
