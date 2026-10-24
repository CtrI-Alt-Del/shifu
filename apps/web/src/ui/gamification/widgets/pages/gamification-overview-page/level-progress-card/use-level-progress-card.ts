import { type Transition, useReducedMotion } from 'motion/react'

import { useFormatXp } from '@/ui/shared/hooks/use-format-xp'

// Width is not a transform, so `MotionConfig reducedMotion='user'` would still
// animate it; the reduced-motion preference is honoured explicitly instead.
const FILL_TRANSITION: Transition = {
  duration: 0.9,
  delay: 0.45,
  ease: [0.16, 1, 0.3, 1],
}

export function useLevelProgressCard() {
  const { formatXp } = useFormatXp()
  const prefersReducedMotion = useReducedMotion()

  return {
    formatXp,
    // With reduced motion the fill renders at its final width on first paint.
    fillInitial: prefersReducedMotion ? (false as const) : { width: '0%' },
    fillTransition: FILL_TRANSITION,
  }
}
