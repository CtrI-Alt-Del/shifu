import { useReducedMotion } from 'motion/react'

export function useMotionEntrance() {
  const prefersReducedMotion = useReducedMotion()

  // `false` renders every variant child in its final state on first paint, so
  // people who ask for less motion see the tab without any entrance.
  return { initial: prefersReducedMotion ? (false as const) : 'hidden' }
}
