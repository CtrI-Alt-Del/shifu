import { motion } from 'motion/react'

import { ENTRANCE_SECTION } from '@/constants/motion-variants'

import type { CompetencyRowView } from '../use-skill-completion'
import { SkillCompletionCompetencyRow } from './skill-completion-competency-row'

export type SkillCompletionCompetencyListProps = {
  competencies: CompetencyRowView[]
}

export const SkillCompletionCompetencyList = ({
  competencies,
}: SkillCompletionCompetencyListProps) => {
  return (
    <motion.section
      aria-labelledby='skill-completion-competencies-title'
      variants={ENTRANCE_SECTION}
    >
      <h2 className='sr-only' id='skill-completion-competencies-title'>
        Competências desta Habilidade
      </h2>
      <ul className='flex flex-col rounded-xl border border-border bg-surface-alt p-2'>
        {competencies.map((competency) => (
          <SkillCompletionCompetencyRow
            competency={competency}
            key={competency.competencyId}
          />
        ))}
      </ul>
    </motion.section>
  )
}
