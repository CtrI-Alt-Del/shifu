import {
  type CompetencyCompletionOverview,
  SKILL_STATUS_LABELS,
  type StartingPointCoverage,
} from '@/core/learning/skill-experience'
import { useFormatDate } from '@/ui/shared/hooks/use-format-date'

import type { SkillCompletionProps } from '.'

export type SkillCompletionKind = 'evolution' | 'diagnosis' | 'partial'

export type IndicatorView = {
  id: 'duration' | 'activities' | 'attempts'
  label: string
  value: number
  format: (value: number) => string
}

export type LegendTone = 'start' | 'evolution' | 'unknown'

export type LegendItemView = {
  id: string
  label: string
  tone: LegendTone
}

export type ComparisonView = {
  initialText: string
  finalText: string
  sign: '→' | '='
  signLabel: 'para' | 'igual a'
  finalTone: 'rose' | 'neutral'
  startingPercent: number
  gainPercent: number
  unknownPercent: number
}

export type OverallView = ComparisonView & {
  label: string
  startingLabel: string | null
}

export type CompetencyRowView = ComparisonView & {
  competencyId: string
  competencyName: string
  startingLabel: string | null
  masteryText: string
  accessibleName: string
  params: { goalId: string; skillId: string; competencyId: string }
}

export type ReviewStatView = {
  id: 'attempts' | 'latest-score'
  value: number
  label: string
}

export type ReviewView = {
  title: string
  notice: string
  stats: ReviewStatView[]
}

const PARTIAL_START_LABEL = 'Ponto de partida parcial'
const UNKNOWN_START_LABEL = 'Ponto de partida desconhecido'

const INTRO_BY_KIND: Record<SkillCompletionKind, string> = {
  evolution:
    'Compare o ponto de partida com o resultado final. A prática continua liberada, mas novas notas não alteram este resumo.',
  diagnosis:
    'Você concluiu esta Habilidade no diagnóstico, por isso o ponto de partida e o resultado final são iguais. A prática continua liberada, mas novas notas não alteram este resumo.',
  partial:
    'Compare o ponto de partida com o resultado final. O diagnóstico não observou todas as dificuldades, então parte do ponto de partida é parcial ou desconhecida. A prática continua liberada, mas novas notas não alteram este resumo.',
}

const REVIEW_TITLE = 'Prática de revisão'
const REVIEW_NOTICE_WITH_ATTEMPTS =
  'Notas de revisão ficam no histórico e não alteram o resultado oficial desta Habilidade.'
const REVIEW_NOTICE_WITHOUT_ATTEMPTS =
  'Você ainda não fez revisões. A prática continua disponível, e as notas de revisão não alteram o resultado oficial desta Habilidade.'

export function useSkillCompletion({
  goalId,
  skillId,
  skillName,
  completion,
}: SkillCompletionProps) {
  const { formatCompactDayLabel } = useFormatDate()

  const isDiagnosisCompletion = completion.completedByDiagnosis
  const hasIncompleteStartingPoint =
    completion.initialResultCoverage !== 'complete' ||
    completion.competencies.some(
      (competency) => competency.initialCoverage !== 'complete',
    )
  const kind: SkillCompletionKind = isDiagnosisCompletion
    ? 'diagnosis'
    : hasIncompleteStartingPoint
      ? 'partial'
      : 'evolution'

  function clampPercent(value: number) {
    return Math.max(0, Math.min(100, Math.round(value)))
  }

  function getStartingLabel(
    initialProgress: number | null,
    coverage: StartingPointCoverage,
  ) {
    if (isDiagnosisCompletion) return null
    if (initialProgress === null) return UNKNOWN_START_LABEL
    return coverage === 'complete' ? null : PARTIAL_START_LABEL
  }

  function buildComparison(
    initialProgress: number | null,
    finalProgress: number,
  ): ComparisonView {
    const final = clampPercent(finalProgress)
    const finalText = `${final}%`

    if (isDiagnosisCompletion)
      return {
        initialText: finalText,
        finalText,
        sign: '=',
        signLabel: 'igual a',
        finalTone: 'neutral',
        startingPercent: final,
        gainPercent: 0,
        unknownPercent: 0,
      }

    if (initialProgress === null)
      return {
        initialText: '—',
        finalText,
        sign: '→',
        signLabel: 'para',
        finalTone: 'neutral',
        startingPercent: 0,
        gainPercent: 0,
        unknownPercent: final,
      }

    const initial = clampPercent(initialProgress)

    return {
      initialText: `${initial}%`,
      finalText,
      sign: '→',
      signLabel: 'para',
      finalTone: final > initial ? 'rose' : 'neutral',
      startingPercent: Math.min(initial, final),
      gainPercent: Math.max(final - initial, 0),
      unknownPercent: 0,
    }
  }

  function describeComparison(
    comparison: ComparisonView,
    initialProgress: number | null,
  ) {
    if (comparison.sign === '=') return `Inicial e final ${comparison.finalText}`
    if (initialProgress === null)
      return `Inicial desconhecido, final ${comparison.finalText}`
    return `Inicial ${comparison.initialText}, final ${comparison.finalText}`
  }

  function buildCompetencyRow(
    competency: CompetencyCompletionOverview,
  ): CompetencyRowView {
    const comparison = buildComparison(
      competency.initialProgress,
      competency.finalProgress,
    )
    const startingLabel = getStartingLabel(
      competency.initialProgress,
      competency.initialCoverage,
    )
    const masteryText = `Dominada em ${formatCompactDayLabel(competency.masteredOn)}`
    const accessibleName = `${[
      competency.competencyName,
      startingLabel,
      masteryText,
      describeComparison(comparison, competency.initialProgress),
    ]
      .filter(Boolean)
      .join('. ')}.`

    return {
      ...comparison,
      competencyId: competency.competencyId,
      competencyName: competency.competencyName,
      startingLabel,
      masteryText,
      accessibleName,
      params: { goalId, skillId, competencyId: competency.competencyId },
    }
  }

  function formatDuration(days: number) {
    if (completion.durationDays === 0) return 'No mesmo dia'
    return `${days} ${days === 1 ? 'dia' : 'dias'}`
  }

  function formatCount(value: number) {
    return String(value)
  }

  const startedDay = formatCompactDayLabel(completion.startedOn)
  const completedDay = formatCompactDayLabel(completion.completedOn)
  const statusLabel = SKILL_STATUS_LABELS.completed
  const dateRange = `${startedDay} → ${completedDay}`
  const dateRangeLabel = `De ${startedDay} a ${completedDay}`
  const intro = INTRO_BY_KIND[kind]

  const indicators: IndicatorView[] = [
    {
      id: 'duration',
      label: 'Do início à conclusão',
      value: completion.durationDays,
      format: formatDuration,
    },
  ]
  if (!isDiagnosisCompletion && completion.learningActivityCount !== null)
    indicators.push({
      id: 'activities',
      label: 'Atividades de aprendizagem feitas',
      value: completion.learningActivityCount,
      format: formatCount,
    })
  if (!isDiagnosisCompletion && completion.learningAttemptCount !== null)
    indicators.push({
      id: 'attempts',
      label: 'Tentativas enviadas até a conclusão',
      value: completion.learningAttemptCount,
      format: formatCount,
    })

  const legendItems: LegendItemView[] =
    kind === 'diagnosis'
      ? [{ id: 'start', label: 'Ponto de partida = resultado final', tone: 'start' }]
      : [
          { id: 'start', label: 'Ponto de partida', tone: 'start' },
          { id: 'evolution', label: 'Evolução até agora', tone: 'evolution' },
          ...(kind === 'partial'
            ? [
                {
                  id: 'unknown',
                  label: 'Resultado sem ponto de partida',
                  tone: 'unknown' as const,
                },
              ]
            : []),
        ]

  const overall: OverallView = {
    ...buildComparison(completion.initialResult, completion.finalResult),
    label: 'Resultado geral da Habilidade',
    startingLabel: getStartingLabel(
      completion.initialResult,
      completion.initialResultCoverage,
    ),
  }

  const competencies = [...completion.competencies]
    .sort((first, second) => first.position - second.position)
    .map(buildCompetencyRow)

  const { attemptCount, latestScore } = completion.review
  const reviewStats: ReviewStatView[] = []
  if (attemptCount > 0) {
    reviewStats.push({
      id: 'attempts',
      value: attemptCount,
      label: attemptCount === 1 ? 'tentativa de revisão' : 'tentativas de revisão',
    })
    if (latestScore !== null)
      reviewStats.push({
        id: 'latest-score',
        value: Math.round(latestScore),
        label: 'última nota de revisão',
      })
  }
  const review: ReviewView = {
    title: REVIEW_TITLE,
    notice:
      attemptCount > 0 ? REVIEW_NOTICE_WITH_ATTEMPTS : REVIEW_NOTICE_WITHOUT_ATTEMPTS,
    stats: reviewStats,
  }

  return {
    skillName,
    statusLabel,
    dateRange,
    dateRangeLabel,
    intro,
    kind,
    indicators,
    legendItems,
    overall,
    competencies,
    review,
    goalParams: { goalId },
  }
}
