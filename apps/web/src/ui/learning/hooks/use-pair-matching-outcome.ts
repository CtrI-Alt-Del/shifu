import type { PairMatchingOutcome } from '@/core/learning/choice-activity'
import type { IconName } from '@/ui/shared/widgets/components/icon'

export type UsePairMatchingOutcomeProps = {
  correctPairCount: number | undefined
  outcome: PairMatchingOutcome | undefined
  totalPairCount: number | undefined
}

const OUTCOME_PRESENTATION: Record<
  PairMatchingOutcome,
  { iconName: IconName; label: string }
> = {
  full: { iconName: 'circle-check', label: 'Resposta correta' },
  partial: { iconName: 'circle-alert', label: 'Parcialmente correta' },
  incorrect: { iconName: 'x', label: 'Resposta incorreta' },
}

export function usePairMatchingOutcome({
  correctPairCount,
  outcome,
  totalPairCount,
}: UsePairMatchingOutcomeProps) {
  if (
    outcome === undefined ||
    correctPairCount === undefined ||
    totalPairCount === undefined
  )
    return null

  return {
    outcome,
    ...OUTCOME_PRESENTATION[outcome],
    countText: `${correctPairCount} de ${totalPairCount} ${totalPairCount === 1 ? 'par correto' : 'pares corretos'}`,
  }
}
