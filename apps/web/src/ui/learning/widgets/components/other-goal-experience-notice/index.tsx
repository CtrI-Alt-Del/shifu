import { Link } from '@tanstack/react-router'
import type { ReactNode } from 'react'

import type { SkillExperienceReference } from '@/core/learning/skill-experience-reference'
import { SKILL_STATUS_PRESENTATION } from '@/ui/learning/constants/skill-status-presentation'
import { Icon } from '@/ui/shared/widgets/components/icon'

export type OtherGoalExperienceNoticeProps = {
  experiences: SkillExperienceReference[]
}

const NOTICE_TITLE = 'Você já tem esta Habilidade em outro Objetivo'
const NOTICE_EXPLANATION =
  'Aqui ela começa do zero, com um novo diagnóstico, e nenhum resultado é copiado.'

export const OtherGoalExperienceNotice = ({
  experiences,
}: OtherGoalExperienceNoticeProps): ReactNode => {
  if (experiences.length === 0) return null

  const hasSeveralExperiences = experiences.length > 1

  return (
    <section
      aria-label={NOTICE_TITLE}
      className='flex gap-3 rounded-xl border border-border bg-surface-alt p-4'
    >
      <Icon className='mt-0.5 size-[18px] shrink-0 text-jade-text' name='info' />
      <div className='flex min-w-0 flex-col gap-1'>
        <p className='text-sm font-semibold leading-[1.2] text-foreground'>
          {NOTICE_TITLE}
        </p>
        <p className='text-sm leading-[1.2] text-secondary-foreground'>
          {experiences.map((experience) => (
            <span
              className={hasSeveralExperiences ? 'block' : undefined}
              key={experience.skillExperienceId}
            >
              {`No Objetivo “${experience.goalTitle}”, ela está ${SKILL_STATUS_PRESENTATION[experience.status].label.toLowerCase()}. `}
            </span>
          ))}
          <span className={hasSeveralExperiences ? 'mt-1 block' : undefined}>
            {NOTICE_EXPLANATION}
          </span>
        </p>
        <ul className='flex flex-col'>
          {experiences.map((experience) => (
            <li key={experience.skillExperienceId}>
              <Link
                className='inline-flex min-h-11 items-center text-sm font-medium text-foreground underline underline-offset-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring sm:min-h-6'
                params={{ goalId: experience.goalId, skillId: experience.skillId }}
                to='/learning/goals/$goalId/skills/$skillId'
              >
                Ver em {experience.goalTitle}
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
