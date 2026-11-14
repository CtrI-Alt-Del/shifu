import { useReducedMotion } from 'motion/react'

// Application boundary for the viewer's "reduce motion" setting. Animated
// widgets read it here, and their tests mock this hook instead of Motion.
export function useReducedMotionPreference() {
  const prefersReducedMotion = useReducedMotion() ?? false

  return { prefersReducedMotion }
}
