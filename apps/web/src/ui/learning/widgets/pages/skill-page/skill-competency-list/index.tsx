import { useState } from 'react'

import type { SkillCompetencySummary } from '@/core/learning/skill-experience'

import { SkillCompetencyRow } from './skill-competency-row'

export type SkillCompetencyListProps = {
  competencies: SkillCompetencySummary[]
  focusCompetencyName: string | null
  goalId: string
  skillId: string
}

export const SkillCompetencyList = ({
  competencies,
  focusCompetencyName,
  goalId,
  skillId,
}: SkillCompetencyListProps) => {
  const [blocked, setBlocked] = useState<SkillCompetencySummary | null>(null)

  return (
    <section aria-labelledby='skill-competencies-title'>
      <h2 className='sr-only' id='skill-competencies-title'>
        Competências desta Habilidade
      </h2>
      <ul className='flex flex-col rounded-[10px] bg-surface-alt p-1.5'>
        {competencies.map((competency) => (
          <SkillCompetencyRow
            competency={competency}
            goalId={goalId}
            key={competency.competencyId}
            onBlockedSelect={setBlocked}
            skillId={skillId}
          />
        ))}
      </ul>
      <p
        className={blocked ? 'mt-3 text-sm text-selo-text' : 'sr-only'}
        id='skill-blocked-hint'
        role={blocked ? 'alert' : undefined}
      >
        {blocked
          ? `${blocked.competencyName} ainda está bloqueada.${
              focusCompetencyName
                ? ` Avance em ${focusCompetencyName} para liberar o conteúdo dela.`
                : ' Conclua as Competências anteriores para liberar o conteúdo dela.'
            }`
          : 'Uma Competência bloqueada explica o requisito de liberação sem sair desta página.'}
      </p>
    </section>
  )
}
