import {
  type DragEndEvent,
  PointerSensor,
  TouchSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import { useEffect, useState } from 'react'
import type { OrderingQuestion as OrderingQuestionData } from '@/core/learning/choice-activity'

export const STEP_DRAG_PREFIX = 'step:'

const POINTER_DRAG_DISTANCE = 8
const TOUCH_DRAG_DELAY_MS = 200
const TOUCH_DRAG_TOLERANCE = 8

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
  const [moveCount, setMoveCount] = useState(0)
  const sortableIds = order.map((stepKey) => `${STEP_DRAG_PREFIX}${stepKey}`)
  // Keyboard and assistive technology keep the move buttons; drag is for pointer and touch.
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: POINTER_DRAG_DISTANCE },
    }),
    useSensor(TouchSensor, {
      activationConstraint: {
        delay: TOUCH_DRAG_DELAY_MS,
        tolerance: TOUCH_DRAG_TOLERANCE,
      },
    }),
  )

  useEffect(() => {
    setOrder(initialOrder)
  }, [initialOrder])

  function commitMove(stepKey: string, nextIndex: number): boolean {
    if (disabled) return false
    const currentIndex = order.indexOf(stepKey)
    if (
      currentIndex < 0 ||
      nextIndex < 0 ||
      nextIndex >= order.length ||
      nextIndex === currentIndex
    ) {
      return false
    }

    const nextOrder = order.filter((key) => key !== stepKey)
    nextOrder.splice(nextIndex, 0, stepKey)
    setOrder(nextOrder)
    onOrderChange?.(nextOrder)
    const step = question.steps.find(({ key }) => key === stepKey)
    setAnnouncement(
      `${step?.text ?? 'Etapa'} agora está na posição ${nextIndex + 1} de ${order.length}.`,
    )
    return true
  }

  function handleMoveStep(stepKey: string, offset: -1 | 1) {
    if (commitMove(stepKey, order.indexOf(stepKey) + offset)) {
      setMoveCount((count) => count + 1)
    }
  }

  function handleDragStart() {
    if (disabled) return

    setAnnouncement('Arrastando a etapa. Solte sobre a posição desejada.')
  }

  function handleDragEnd(event: DragEndEvent) {
    const overId = event.over ? String(event.over.id) : null
    if (overId === null || !overId.startsWith(STEP_DRAG_PREFIX)) return

    const stepKey = String(event.active.id).slice(STEP_DRAG_PREFIX.length)
    commitMove(stepKey, order.indexOf(overId.slice(STEP_DRAG_PREFIX.length)))
  }

  function handleDragCancel() {
    setAnnouncement('Arrasto cancelado.')
  }

  return {
    announcement,
    order,
    sensors,
    handleDragCancel,
    handleDragEnd,
    handleDragStart,
    handleMoveStep,
    moveCount,
    sortableIds,
  }
}
