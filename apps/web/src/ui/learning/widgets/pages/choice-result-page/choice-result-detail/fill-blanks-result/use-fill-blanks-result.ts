import type { FillBlanksSegment } from '@/core/learning/choice-activity'
import { useFillBlanksOutcome } from '@/ui/learning/hooks/use-fill-blanks-outcome'

import type { FillBlanksResultProps } from '.'

const SCORE_FORMATTER = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 })

export type FilledSegment = {
  segment: FillBlanksSegment
  blankNumber: number | null
  word: string | null
}

export function useFillBlanksResult({ result }: FillBlanksResultProps) {
  const outcome = useFillBlanksOutcome({
    blankCount: result.blankCount,
    correctBlankCount: result.correctBlankCount,
    score: result.score,
  })
  const wordByKey = new Map(result.bank.map((word) => [word.key, word.word]))
  const placedWordByBlank = new Map(
    result.placements.map((placement) => [
      placement.blankKey,
      wordByKey.get(placement.wordKey) ?? null,
    ]),
  )
  let blankCounter = 0
  const filledSegments: FilledSegment[] = result.segments.map((segment) => {
    if (segment.blankKey === null) return { segment, blankNumber: null, word: null }

    blankCounter += 1
    return {
      segment,
      blankNumber: blankCounter,
      word: placedWordByBlank.get(segment.blankKey) ?? null,
    }
  })
  const blankNumberByKey = new Map(
    filledSegments.flatMap((item) =>
      item.segment.blankKey !== null && item.blankNumber !== null
        ? [[item.segment.blankKey, item.blankNumber] as const]
        : [],
    ),
  )
  const expectedItems = result.expectedBlanks.map((blank) => ({
    blankKey: blank.blankKey,
    blankNumber: blankNumberByKey.get(blank.blankKey) ?? 0,
    words: blank.acceptedWords,
  }))

  return {
    outcome,
    expectedItems,
    filledSegments,
    formattedScore: SCORE_FORMATTER.format(Number(result.score)),
    hasExpectedBlanks: expectedItems.length > 0,
    isCorrect: result.isCorrect,
  }
}
