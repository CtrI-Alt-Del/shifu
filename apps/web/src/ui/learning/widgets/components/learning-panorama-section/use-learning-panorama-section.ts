import type { LearningPanorama } from '@/core/learning/learning-panorama'
import { useLearningPanoramaQuery } from '@/ui/learning/hooks/use-learning-panorama-query'
import { useFormatDate } from '@/ui/shared/hooks/use-format-date'
import type { ChartDatum } from '@/ui/shared/widgets/components/chart-frame'

import type { StageItem } from './stage-distribution-card'

export type LearningPanoramaSectionState = 'loading' | 'error' | 'empty' | 'success'

function pluralize(count: number, singular: string, plural: string): string {
  return `${count} ${count === 1 ? singular : plural}`
}

export function useLearningPanoramaSection() {
  const {
    panorama,
    panoramaError,
    isLoadingPanorama,
    isFetchingPanorama,
    refetchPanorama,
  } = useLearningPanoramaQuery()
  const { formatCompactDayLabel } = useFormatDate()

  const state: LearningPanoramaSectionState = isLoadingPanorama
    ? 'loading'
    : panoramaError || !panorama
      ? 'error'
      : !panorama.hasGoals
        ? 'empty'
        : 'success'
  const readyPanorama: LearningPanorama | null = state === 'success' ? panorama : null

  const weeklyData: ChartDatum[] = (readyPanorama?.weeklyEvaluatedActivities ?? []).map(
    (week) => ({
      key: week.weekStart,
      label: formatCompactDayLabel(week.weekStart),
      value: week.count,
      valueLabel: pluralize(week.count, 'atividade', 'atividades'),
    }),
  )
  // Without a single evaluated activity the axes would be empty, so the card
  // explains that the chart appears after the first evaluations instead.
  const hasWeeklyData = weeklyData.some((week) => week.value > 0)

  const distribution = readyPanorama?.stageDistribution
  const stageItems: StageItem[] = [
    { key: 'not-started', label: 'Não iniciadas', count: distribution?.notStarted ?? 0 },
    { key: 'diagnosing', label: 'Em diagnóstico', count: distribution?.diagnosing ?? 0 },
    { key: 'learning', label: 'Em aprendizado', count: distribution?.learning ?? 0 },
    { key: 'completed', label: 'Concluídas', count: distribution?.completed ?? 0 },
  ]
  const experiencesCount = stageItems.reduce((total, item) => total + item.count, 0)
  const stageSummary =
    experiencesCount === 0
      ? 'Nenhuma Habilidade nos seus Objetivos ainda.'
      : `${pluralize(experiencesCount, 'Habilidade', 'Habilidades')} em ${pluralize(distribution?.goalCount ?? 0, 'Objetivo', 'Objetivos')}`

  function handleRetry() {
    void refetchPanorama()
  }

  return {
    state,
    panorama: readyPanorama,
    isRetrying: isFetchingPanorama && !isLoadingPanorama,
    weeklyData,
    hasWeeklyData,
    stageItems,
    stageSummary,
    handleRetry,
  }
}
