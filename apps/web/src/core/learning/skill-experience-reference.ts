import type { SkillExperienceStatus } from '@/core/learning/skill-experience'

export type SkillExperienceReference = {
  goalId: string
  goalTitle: string
  skillExperienceId: string
  skillId: string
  status: SkillExperienceStatus
}
