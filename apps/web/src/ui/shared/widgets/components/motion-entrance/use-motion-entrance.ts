import { useReducedMotionPreference } from '@/ui/shared/hooks/use-reduced-motion-preference'

export function useMotionEntrance() {
  const { prefersReducedMotion } = useReducedMotionPreference()

  // `false` renders every variant child in its final state on first paint, so
  // people who ask for less motion see the tab without any entrance.
  return { initial: prefersReducedMotion ? (false as const) : 'hidden' }
}
