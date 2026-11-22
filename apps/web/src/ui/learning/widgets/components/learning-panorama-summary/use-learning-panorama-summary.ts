import { useLearningPanoramaQuery } from '@/ui/learning/hooks/use-learning-panorama-query'

export type LearningPanoramaSummaryState = 'loading' | 'error' | 'empty' | 'success'

export type LearningPanoramaSummaryCard = {
  key: 'completed-skills' | 'mastered-competencies'
  caption: string
  value: number
}

const COUNT_FORMATTER = new Intl.NumberFormat('pt-BR')

export function useLearningPanoramaSummary() {
  const {
    panorama,
    panoramaError,
    isLoadingPanorama,
    isFetchingPanorama,
    refetchPanorama,
  } = useLearningPanoramaQuery()

  const state: LearningPanoramaSummaryState = isLoadingPanorama
    ? 'loading'
    : panoramaError || !panorama
      ? 'error'
      : !panorama.hasGoals
        ? 'empty'
        : 'success'

  // Both counts are plain counts of distinct catalog items; without an
  // Objetivo they are zero rather than an invented value.
  const cards: LearningPanoramaSummaryCard[] = [
    {
      key: 'completed-skills',
      caption: 'Habilidades concluídas',
      value: panorama?.completedSkillCount ?? 0,
    },
    {
      key: 'mastered-competencies',
      caption: 'Competências dominadas',
      value: panorama?.masteredCompetencyCount ?? 0,
    },
  ]

  function formatCount(value: number): string {
    return COUNT_FORMATTER.format(value)
  }

  function handleRetry() {
    void refetchPanorama()
  }

  return {
    state,
    cards,
    isRetrying: isFetchingPanorama && !isLoadingPanorama,
    formatCount,
    handleRetry,
  }
}
