import { useReducedMotionPreference } from '@/ui/shared/hooks/use-reduced-motion-preference'

export function useMessageList() {
  const { prefersReducedMotion } = useReducedMotionPreference()

  // `false` shows every card in place at once for people who ask for less
  // motion; otherwise the cards present when the list mounts cascade in and
  // later ones animate as they arrive.
  return { initial: prefersReducedMotion ? (false as const) : 'hidden' }
}
