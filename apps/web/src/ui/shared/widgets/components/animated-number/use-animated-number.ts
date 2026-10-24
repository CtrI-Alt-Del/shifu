import { animate, useReducedMotion } from 'motion/react'
import { useEffect, useRef, useState } from 'react'

import type { AnimatedNumberProps } from '.'

const COUNT_EASE = [0.16, 1, 0.3, 1] as const

export function useAnimatedNumber({
  value,
  format,
  duration = 1.1,
  delay = 0,
}: AnimatedNumberProps) {
  const prefersReducedMotion = useReducedMotion()
  const [current, setCurrent] = useState(prefersReducedMotion ? value : 0)
  const latest = useRef(current)

  useEffect(() => {
    function handleUpdate(next: number) {
      latest.current = next
      setCurrent(next)
    }

    if (prefersReducedMotion) {
      handleUpdate(value)
      return
    }

    // Counts from wherever the number currently is, so a refreshed value
    // continues from the shown figure instead of restarting at zero.
    const controls = animate(latest.current, value, {
      duration,
      delay,
      ease: COUNT_EASE,
      onUpdate: handleUpdate,
    })
    return () => controls.stop()
  }, [value, prefersReducedMotion, duration, delay])

  const rounded = Math.round(current)

  return { text: format ? format(rounded) : String(rounded) }
}
