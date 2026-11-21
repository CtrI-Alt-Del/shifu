import { useEffect, useState } from 'react'
import type { OrderingQuestion as OrderingQuestionData } from '@/core/learning/choice-activity'

export type UseOrderingQuestionProps = {
  question: OrderingQuestionData
  orderedStepKeys?: readonly string[]
  disabled?: boolean
  onOrderChange?: (orderedStepKeys: readonly string[]) => void
}

export const useOrderingQuestion = ({
  disabled = false,
  onOrderChange,
  orderedStepKeys,
  question,
}: UseOrderingQuestionProps) => {
  const initialOrder =
    orderedStepKeys ??
    question.verified?.orderedStepKeys ??
    question.initialOrderedStepKeys
  const [order, setOrder] = useState<readonly string[]>(initialOrder)
  const [announcement, setAnnouncement] = useState('')

  useEffect(() => {
    setOrder(initialOrder)
  }, [initialOrder])

  function handleMoveStep(stepKey: string, offset: -1 | 1) {
    if (disabled) return
    const currentIndex = order.indexOf(stepKey)
    const nextIndex = currentIndex + offset
    if (currentIndex < 0 || nextIndex < 0 || nextIndex >= order.length) return

    const nextOrder = [...order]
    ;[nextOrder[currentIndex], nextOrder[nextIndex]] = [
      nextOrder[nextIndex],
      nextOrder[currentIndex],
    ]
    setOrder(nextOrder)
    onOrderChange?.(nextOrder)
    const step = question.steps.find(({ key }) => key === stepKey)
    setAnnouncement(
      `${step?.text ?? 'Etapa'} agora está na posição ${nextIndex + 1} de ${order.length}.`,
    )
  }

  return { announcement, handleMoveStep, order }
}
