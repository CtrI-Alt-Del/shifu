import type { SkillExperienceStatus } from '@/core/learning/goal-detail'
import { SKILL_STATUS_PRESENTATION } from '@/ui/learning/constants/skill-status-presentation'
import { Icon } from '@/ui/shared/widgets/components/icon'

export type SkillStatusProps = { status: SkillExperienceStatus }

export const SkillStatus = ({ status }: SkillStatusProps) => {
  const presentation = SKILL_STATUS_PRESENTATION[status]

  return (
    <span
      className={`inline-flex items-center gap-2 text-sm font-semibold ${presentation.className}`}
    >
      <Icon name={presentation.iconName} size={16} />
      {presentation.label}
    </span>
  )
}
