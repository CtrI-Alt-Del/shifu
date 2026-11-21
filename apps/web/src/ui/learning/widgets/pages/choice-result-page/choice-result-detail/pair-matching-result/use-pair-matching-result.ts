import { pairMatchingItemText } from '@/core/learning/pair-matching-item-text'
import type { PairMatchingPair } from '@/core/learning/choice-activity'
import { usePairMatchingOutcome } from '@/ui/learning/hooks/use-pair-matching-outcome'

import type { PairMatchingResultProps } from '.'

const SCORE_FORMATTER = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 })

export function usePairMatchingResult({ question, result }: PairMatchingResultProps) {
  const outcome = usePairMatchingOutcome({
    correctPairCount: result.correctPairCount,
    outcome: result.outcome,
    totalPairCount: result.totalPairCount,
  })
  const toItems = (pairs: readonly PairMatchingPair[]) =>
    pairs.map((pair) => ({
      key: pair.wordKey,
      wordText: pairMatchingItemText(question?.words, pair.wordKey),
      translationText: pairMatchingItemText(question?.translations, pair.translationKey),
    }))

  return {
    outcome,
    isFull: result.outcome === 'full',
    formattedScore: SCORE_FORMATTER.format(Number(result.score)),
    submittedItems: toItems(result.submittedPairs),
    expectedItems: toItems(result.disclosedCorrectPairs ?? []),
  }
}
