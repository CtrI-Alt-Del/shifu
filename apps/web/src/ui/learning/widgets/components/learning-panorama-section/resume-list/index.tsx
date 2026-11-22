import { Link } from '@tanstack/react-router'
import { motion } from 'motion/react'

import { ENTRANCE_CARD, ENTRANCE_ROW } from '@/constants/motion-variants'
import { ROUTES } from '@/constants/routes'
import type { ResumeItem } from '@/core/learning/learning-panorama'
import { SKILL_STATUS_LABELS } from '@/core/learning/skill-experience'

export type ResumeListProps = {
  items: ResumeItem[]
}

// "Continue de onde parou" is context, not a recommendation: each item names
// the Habilidade, its Objetivo and stage, and links to the skill page.
export const ResumeList = ({ items }: ResumeListProps) => (
  <motion.section
    aria-labelledby='learning-panorama-resume-title'
    className='flex min-w-0 flex-col gap-4 rounded-[14px] border border-border bg-surface-alt p-5'
    variants={ENTRANCE_CARD}
  >
    <h3
      className='text-base font-semibold text-foreground'
      id='learning-panorama-resume-title'
    >
      Continue de onde parou
    </h3>
    {items.length === 0 ? (
      <p className='text-sm text-muted-foreground'>
        Nenhuma Habilidade em diagnóstico ou em aprendizado no momento.
      </p>
    ) : (
      <ul>
        {items.map((item) => (
          <motion.li
            className='flex flex-col gap-3 border-b border-border py-4 first:pt-0 last:border-b-0 last:pb-0 md:flex-row md:items-center md:justify-between md:gap-4'
            key={item.skillExperienceId}
            variants={ENTRANCE_ROW}
          >
            <div className='min-w-0 space-y-1'>
              <p
                className='text-[15px] font-semibold text-foreground'
                id={`learning-panorama-resume-${item.skillExperienceId}`}
              >
                {item.skillName}
              </p>
              <p className='text-[13px] text-secondary-foreground'>
                Objetivo: {item.goalTitle}
                {item.focusCompetencyName ? ` · Foco: ${item.focusCompetencyName}` : ''}
              </p>
              <p className='text-[13px] text-muted-foreground'>
                {SKILL_STATUS_LABELS[item.status]}
              </p>
            </div>
            <Link
              aria-describedby={`learning-panorama-resume-${item.skillExperienceId}`}
              className='inline-flex min-h-11 shrink-0 items-center justify-center rounded-md border border-control-border px-4 text-sm font-semibold text-foreground transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40'
              params={{ goalId: item.goalId, skillId: item.skillId }}
              to={ROUTES.learningSkill}
            >
              Continuar
            </Link>
          </motion.li>
        ))}
      </ul>
    )}
  </motion.section>
)
