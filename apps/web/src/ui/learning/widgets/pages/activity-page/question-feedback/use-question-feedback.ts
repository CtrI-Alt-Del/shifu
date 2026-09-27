import { useEffect, useRef } from 'react'

import type { ActivityQuestion } from '@/core/learning/choice-activity'

export type UseQuestionFeedbackProps = {
  question: ActivityQuestion
}

export function useQuestionFeedback({ question }: UseQuestionFeedbackProps) {
  const feedbackElementRef = useRef<HTMLElement>(null)

  useEffect(() => {
    if (question.kind !== 'javascript_stdin') return

    feedbackElementRef.current?.scrollIntoView({
      behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches
        ? 'auto'
        : 'smooth',
      block: 'start',
    })
  }, [question.kind])

  return { feedbackElementRef }
}
