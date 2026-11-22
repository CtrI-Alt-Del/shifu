import { Link } from '@tanstack/react-router'
import { motion } from 'motion/react'

import { ENTRANCE_CARD, ENTRANCE_ROW } from '@/constants/motion-variants'
import { ROUTES } from '@/constants/routes'
import type { CompletedSkill } from '@/core/learning/learning-panorama'
import { useFormatDate } from '@/ui/shared/hooks/use-format-date'
import { Icon } from '@/ui/shared/widgets/components/icon'

export type CompletedSkillsCardProps = {
  skills: CompletedSkill[]
}

// The columns follow the board: Habilidade, Objetivo, Concluída em and
// Resultado final. Each row opens the skill page, where the preserved final
// summary of the experience is shown.
const ROW_COLUMNS =
  'md:grid md:grid-cols-[minmax(0,3fr)_minmax(0,2fr)_minmax(0,1.2fr)] md:items-center md:gap-4'

export const CompletedSkillsCard = ({ skills }: CompletedSkillsCardProps) => {
  const { formatCompactDayLabel } = useFormatDate()

  return (
    <motion.section
      aria-labelledby='learning-panorama-completed-title'
      className='flex min-w-0 flex-col gap-2 rounded-[14px] border border-border bg-surface-alt p-5'
      variants={ENTRANCE_CARD}
    >
      <h3
        className='text-base font-semibold text-foreground'
        id='learning-panorama-completed-title'
      >
        Habilidades concluídas
      </h3>
      {skills.length === 0 ? (
        <p className='pt-2 text-sm text-muted-foreground'>
          Você ainda não concluiu nenhuma Habilidade.
        </p>
      ) : (
        <>
          <div
            aria-hidden='true'
            className='hidden gap-4 border-b border-border py-1 text-xs font-medium text-muted-foreground md:flex'
          >
            <span className={`min-w-0 flex-1 ${ROW_COLUMNS}`}>
              <span>Habilidade</span>
              <span>Objetivo</span>
              <span>Concluída em</span>
            </span>
            <span className='w-[120px] text-right'>Resultado final</span>
            <span className='size-4' />
          </div>
          <ul>
            {skills.map((skill) => (
              <motion.li
                className='border-b border-border last:border-b-0'
                key={skill.skillExperienceId}
                variants={ENTRANCE_ROW}
              >
                <Link
                  className='flex items-center gap-4 py-3 transition-colors md:py-[22px] hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40'
                  params={{ goalId: skill.goalId, skillId: skill.skillId }}
                  to={ROUTES.learningSkill}
                >
                  <span className={`grid min-w-0 flex-1 gap-0.5 ${ROW_COLUMNS}`}>
                    <span className='text-[15px] font-medium text-foreground'>
                      {skill.skillName}
                    </span>
                    <span className='flex flex-wrap gap-x-2 text-sm text-secondary-foreground md:contents'>
                      <span>
                        <span className='sr-only'>Objetivo: </span>
                        {skill.goalTitle}
                      </span>
                      <span aria-hidden='true' className='md:hidden'>
                        ·
                      </span>
                      <span>
                        <span className='sr-only'>Concluída em </span>
                        {formatCompactDayLabel(skill.completedOn)}
                      </span>
                    </span>
                  </span>
                  <span className='text-right md:w-[120px]'>
                    <span className='block font-mono text-[15px] font-semibold text-jade-text'>
                      {skill.finalResult === null
                        ? '—'
                        : `${Math.round(skill.finalResult)}%`}
                    </span>
                    <span className='block text-xs text-muted-foreground md:sr-only'>
                      resultado final
                    </span>
                  </span>
                  <Icon
                    className='shrink-0 text-muted-foreground'
                    name='chevron-right'
                    size={16}
                  />
                </Link>
              </motion.li>
            ))}
          </ul>
        </>
      )}
    </motion.section>
  )
}
