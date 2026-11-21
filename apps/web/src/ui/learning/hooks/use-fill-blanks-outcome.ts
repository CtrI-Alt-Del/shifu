import type { IconName } from '@/ui/shared/widgets/components/icon'

export type FillBlanksOutcomeBand = 'correct' | 'partial' | 'incorrect'

export type UseFillBlanksOutcomeProps = {
  blankCount: number | undefined
  correctBlankCount: number | undefined
  score: number | null | undefined
}

const OUTCOME_BY_BAND: Record<
  FillBlanksOutcomeBand,
  { iconName: IconName; label: string }
> = {
  correct: { iconName: 'circle-check', label: 'Resposta correta' },
  partial: { iconName: 'circle-alert', label: 'Parcialmente correta' },
  incorrect: { iconName: 'x', label: 'Resposta incorreta' },
}

export function useFillBlanksOutcome({
  blankCount,
  correctBlankCount,
  score,
}: UseFillBlanksOutcomeProps) {
  if (blankCount === undefined || correctBlankCount === undefined) return null

  const numericScore = Number(score ?? 0)
  const band: FillBlanksOutcomeBand =
    numericScore >= 100 ? 'correct' : numericScore > 0 ? 'partial' : 'incorrect'

  return {
    band,
    ...OUTCOME_BY_BAND[band],
    countText: `${correctBlankCount} de ${blankCount} ${blankCount === 1 ? 'lacuna correta' : 'lacunas corretas'}`,
  }
}
