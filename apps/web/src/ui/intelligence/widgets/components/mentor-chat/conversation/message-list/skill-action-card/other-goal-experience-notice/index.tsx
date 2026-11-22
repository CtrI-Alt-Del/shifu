import { Link } from '@tanstack/react-router'

import { ROUTES } from '@/constants/routes'
import { SKILL_STATUS_LABELS } from '@/core/learning/skill-experience'
import type { SkillExperienceReference } from '@/core/learning/skill-experience-reference'
import { Icon } from '@/ui/shared/widgets/components/icon'

export type OtherGoalExperienceNoticeProps = {
  experiences: SkillExperienceReference[]
}

export const OtherGoalExperienceNotice = ({
  experiences,
}: OtherGoalExperienceNoticeProps) => {
  if (experiences.length === 0) return null

  return (
    <div
      className='flex items-start gap-3 rounded-[12px] border border-border bg-surface-alt p-4'
      role='note'
    >
      <span className='mt-px flex shrink-0 text-jade-text'>
        <Icon name='info' size={18} />
      </span>
      <div className='flex min-w-0 flex-col items-start gap-1'>
        <p className='text-sm font-semibold text-foreground'>
          Você já tem esta Habilidade em outro Objetivo
        </p>
        <p className='break-words text-sm text-secondary-foreground'>
          {experiences.map((experience) => (
            <span key={experience.skillExperienceId}>
              {`No Objetivo “${experience.goalTitle}”, ela está ${SKILL_STATUS_LABELS[experience.status].toLowerCase()}. `}
            </span>
          ))}
          Aqui ela começa do zero, com um novo diagnóstico, e nenhum resultado é copiado.
        </p>
        {experiences.map((experience) => (
          <Link
            className='break-words rounded-sm text-sm font-medium text-foreground underline underline-offset-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-selo-text'
            key={experience.skillExperienceId}
            params={{ goalId: experience.goalId, skillId: experience.skillId }}
            to={ROUTES.learningSkill}
          >
            {`Ver em ${experience.goalTitle}`}
          </Link>
        ))}
      </div>
    </div>
  )
}
