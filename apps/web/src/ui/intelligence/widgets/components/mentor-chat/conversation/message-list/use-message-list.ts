import { useReducedMotion } from 'motion/react'

export function useMessageList() {
  const prefersReducedMotion = useReducedMotion()

  // `false` shows every card in place at once for people who ask for less
  // motion; otherwise the cards present when the list mounts cascade in and
  // later ones animate as they arrive.
  return { initial: prefersReducedMotion ? (false as const) : 'hidden' }
}
