import { useState } from 'react'

import type { SkillEvolutionPoint } from '@/core/learning/skill-evolution'
import type { ChartDatum } from '@/ui/shared/widgets/components/chart-frame'

import type { SkillEvolutionCardProps } from '.'
import { useSkillEvolutionQuery } from './use-skill-evolution-query'

export type SkillEvolutionCardState = 'loading' | 'error' | 'empty' | 'success'

const POINT_DATE_FORMATTER = new Intl.DateTimeFormat('pt-BR', {
  day: 'numeric',
  month: 'short',
})
// A lone diagnostic base point is not an evolution yet (RF-10).
const MIN_POINTS_FOR_EVOLUTION = 2
const PARTIAL_NOTE = 'Parcial'
const BASELINE_DESCRIPTION =
  'Resultado da Habilidade após cada avaliação, desde o diagnóstico · pontos vazados são estimativas parciais'
const NO_BASELINE_DESCRIPTION =
  'Resultado da Habilidade após cada avaliação · pontos vazados são estimativas parciais'

export function useSkillEvolutionCard({
  options,
  defaultSkillExperienceId,
}: SkillEvolutionCardProps) {
  const [chosenSkillExperienceId, setChosenSkillExperienceId] = useState<string | null>(
    defaultSkillExperienceId,
  )
  // A choice that left the panorama (for example a removed experience) falls
  // back to the default instead of querying an experience that is gone.
  const selectedSkillExperienceId = options.some(
    (option) => option.skillExperienceId === chosenSkillExperienceId,
  )
    ? chosenSkillExperienceId
    : defaultSkillExperienceId
  const {
    skillEvolution,
    skillEvolutionError,
    isLoadingSkillEvolution,
    isFetchingSkillEvolution,
    refetchSkillEvolution,
  } = useSkillEvolutionQuery(selectedSkillExperienceId)

  // The same Habilidade can sit in two Objetivos, so the Objetivo is only
  // added to the label when the name alone would be ambiguous.
  const selectOptions = options.map((option) => {
    const isAmbiguous =
      options.filter((other) => other.skillName === option.skillName).length > 1
    return {
      value: option.skillExperienceId,
      label: isAmbiguous ? `${option.skillName} · ${option.goalTitle}` : option.skillName,
    }
  })

  const points: SkillEvolutionPoint[] = skillEvolution?.points ?? []
  const baseline = points.find((point) => point.isBaseline)
  const evolutionData: ChartDatum[] = points.map((point, index) => ({
    key: `${point.occurredAt}-${index}`,
    label: formatPointDate(point.occurredAt),
    value: point.result,
    valueLabel: point.isBaseline
      ? `${formatResult(point.result)} (ponto de partida)`
      : formatResult(point.result),
    note: point.isPartial ? PARTIAL_NOTE : undefined,
  }))
  const baselineLabel = baseline
    ? `Ponto de partida · ${formatResult(baseline.result)}`
    : undefined
  const description = baseline ? BASELINE_DESCRIPTION : NO_BASELINE_DESCRIPTION

  const state: SkillEvolutionCardState =
    selectedSkillExperienceId === null
      ? 'empty'
      : isLoadingSkillEvolution
        ? 'loading'
        : skillEvolutionError || !skillEvolution
          ? 'error'
          : points.length < MIN_POINTS_FOR_EVOLUTION
            ? 'empty'
            : 'success'

  function formatResult(result: number): string {
    return `${Math.round(result)}%`
  }

  // pt-BR renders "28 de set."; the board writes "28 set".
  function formatPointDate(occurredAt: string): string {
    return POINT_DATE_FORMATTER.format(new Date(occurredAt))
      .replaceAll(' de ', ' ')
      .replace('.', '')
  }

  function handleSelectSkillExperience(skillExperienceId: string | null) {
    if (skillExperienceId) setChosenSkillExperienceId(skillExperienceId)
  }

  function handleRetry() {
    void refetchSkillEvolution()
  }

  return {
    state,
    selectedSkillExperienceId,
    selectOptions,
    evolutionData,
    baselineLabel,
    description,
    isRetrying: isFetchingSkillEvolution && !isLoadingSkillEvolution,
    handleSelectSkillExperience,
    handleRetry,
  }
}
