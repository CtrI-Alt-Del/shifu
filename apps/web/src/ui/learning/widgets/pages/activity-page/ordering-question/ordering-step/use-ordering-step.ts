import { useSortable } from '@dnd-kit/sortable'

import { useReducedMotionPreference } from '@/ui/shared/hooks/use-reduced-motion-preference'

import { STEP_DRAG_PREFIX } from '../use-ordering-question'

import type { OrderingStepProps } from '.'

const SORT_TRANSITION = { duration: 220, easing: 'cubic-bezier(0.22, 1, 0.36, 1)' }

export function useOrderingStep({ disabled, isVerified, step }: OrderingStepProps) {
  const { prefersReducedMotion } = useReducedMotionPreference()
  const { isDragging, listeners, setNodeRef, transform, transition } = useSortable({
    disabled: disabled || isVerified,
    id: `${STEP_DRAG_PREFIX}${step.key}`,
    transition: prefersReducedMotion ? null : SORT_TRANSITION,
  })
  const style = {
    transform: transform
      ? `translate3d(${transform.x}px, ${transform.y}px, 0)`
      : undefined,
    transition: prefersReducedMotion ? undefined : transition,
  }

  return { isDragging, listeners, prefersReducedMotion, style, setNodeRef }
}
