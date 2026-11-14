export type MentorSkillActionOutcome = {
  confirmationId: string
  operation: 'add_skill' | 'remove_skill'
  outcome: 'added' | 'already_present' | 'removed' | 'rejected'
  rejectionReason:
    | 'goal_unavailable'
    | 'skill_unavailable'
    | 'experience_unavailable'
    | null
  goalId: string
  skillId: string | null
  skillExperienceId: string | null
}
