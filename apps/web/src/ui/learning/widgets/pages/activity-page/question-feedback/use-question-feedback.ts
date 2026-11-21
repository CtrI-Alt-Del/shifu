import { useEffect, useRef } from 'react'

import type {
  ActivityQuestion,
  PreliminaryQuestionResult,
} from '@/core/learning/choice-activity'
import { useFillBlanksOutcome } from '@/ui/learning/hooks/use-fill-blanks-outcome'
import { usePairMatchingOutcome } from '@/ui/learning/hooks/use-pair-matching-outcome'

export type UseQuestionFeedbackProps = {
  feedback: PreliminaryQuestionResult
  question: ActivityQuestion
}

export function useQuestionFeedback({ feedback, question }: UseQuestionFeedbackProps) {
  const feedbackElementRef = useRef<HTMLElement>(null)
  const fillBlanksOutcome = useFillBlanksOutcome({
    blankCount: feedback.blankCount,
    correctBlankCount: feedback.correctBlankCount,
    score: feedback.score,
  })

  const pairMatchingOutcome = usePairMatchingOutcome({
    correctPairCount: feedback.correctPairCount,
    outcome: feedback.outcome,
    totalPairCount: feedback.totalPairCount,
  })

  useEffect(() => {
    if (
      question.kind !== 'javascript_stdin' &&
      question.kind !== 'react' &&
      question.kind !== 'react_fastify'
    )
      return

    feedbackElementRef.current?.scrollIntoView({
      behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches
        ? 'auto'
        : 'smooth',
      block: 'start',
    })
  }, [question.kind])

  return { feedbackElementRef, fillBlanksOutcome, pairMatchingOutcome }
}
