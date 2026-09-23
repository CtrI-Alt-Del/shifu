import { useHomeGoalsQuery } from '@/ui/intelligence/hooks/use-home-goals-query'

export type GoalsListSectionState = 'empty' | 'error' | 'loading' | 'populated'

export function useGoalsListSection() {
  const { goals, goalsError, isLoadingGoals, refetchGoals } = useHomeGoalsQuery()

  const state = resolveGoalsListSectionState({
    goalsCount: goals.length,
    hasError: Boolean(goalsError),
    isLoading: isLoadingGoals,
  })

  function handleRetry() {
    refetchGoals()
  }

  return {
    goals,
    goalsCountLabel: formatGoalsCountLabel(goals.length),
    state,
    handleRetry,
  }
}

function resolveGoalsListSectionState(input: {
  goalsCount: number
  hasError: boolean
  isLoading: boolean
}): GoalsListSectionState {
  if (input.isLoading) return 'loading'
  if (input.hasError) return 'error'
  if (input.goalsCount === 0) return 'empty'
  return 'populated'
}

function formatGoalsCountLabel(count: number) {
  return count === 1 ? '1 objetivo' : `${count} objetivos`
}
