import type { SkillExperienceStatus } from '@/core/learning/goal-detail'
import { SKILL_STATUS_PRESENTATION } from '@/ui/learning/constants/skill-status-presentation'

export type SkillStatusProps = { status: SkillExperienceStatus }

export const SkillStatus = ({ status }: SkillStatusProps) => {
  const presentation = SKILL_STATUS_PRESENTATION[status]

  return (
    <span className={`text-sm font-semibold ${presentation.className}`}>
      {presentation.label}
    </span>
  )
}
