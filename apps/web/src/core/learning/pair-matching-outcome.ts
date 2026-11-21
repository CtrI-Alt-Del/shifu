import type { PairMatchingOutcome } from './choice-activity'

export const PAIR_MATCHING_OUTCOME_LABELS: Record<PairMatchingOutcome, string> = {
  full: 'Resposta correta',
  partial: 'Parcialmente correta',
  incorrect: 'Resposta incorreta',
}

export const PAIR_MATCHING_OUTCOME_ICONS = {
  full: 'circle-check',
  partial: 'circle-alert',
  incorrect: 'x',
} as const satisfies Record<PairMatchingOutcome, string>
