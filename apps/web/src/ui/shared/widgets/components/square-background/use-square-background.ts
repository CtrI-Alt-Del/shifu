import { useMotionValue, useMotionValueEvent, useSpring } from 'motion/react'
import { useEffect, useRef } from 'react'

type SquareMetric = {
  element: HTMLElement
  proximity: number
  x: number
  y: number
}

const SQUARE_COUNT = 700
const PROXIMITY_RADIUS = 75
const POINTER_SPRING = {
  damping: 28,
  mass: 0.45,
  stiffness: 260,
}

export function useSquareBackground() {
  const backgroundRef = useRef<HTMLDivElement>(null)
  const pointerX = useMotionValue(0)
  const pointerY = useMotionValue(0)
  const smoothPointerX = useSpring(pointerX, POINTER_SPRING)
  const smoothPointerY = useSpring(pointerY, POINTER_SPRING)
  const isActiveRef = useRef(false)
  const pointerMotionValuesRef = useRef({ pointerX, pointerY })
  const squareMetricsRef = useRef<SquareMetric[]>([])

  function updateSquares() {
    const background = backgroundRef.current

    if (!background || !isActiveRef.current) return

    const pointerXValue = smoothPointerX.get()
    const pointerYValue = smoothPointerY.get()
    background.style.setProperty('--pointer-x', `${pointerXValue}px`)
    background.style.setProperty('--pointer-y', `${pointerYValue}px`)

    for (const square of squareMetricsRef.current) {
      const distance = Math.hypot(square.x - pointerXValue, square.y - pointerYValue)
      const proximity = Math.max(0, 1 - distance / PROXIMITY_RADIUS)

      if (Math.abs(square.proximity - proximity) < 0.01) continue

      square.proximity = proximity
      square.element.style.setProperty('--square-proximity', proximity.toFixed(3))
    }
  }

  useMotionValueEvent(smoothPointerX, 'change', updateSquares)
  useMotionValueEvent(smoothPointerY, 'change', updateSquares)

  useEffect(() => {
    const background = backgroundRef.current
    const matchMedia = window.matchMedia?.bind(window)
    const prefersReducedMotion =
      matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false

    if (
      !background ||
      prefersReducedMotion ||
      !(matchMedia?.('(pointer: fine)').matches ?? false)
    ) {
      return
    }

    function measureSquares() {
      const backgroundElement = backgroundRef.current

      if (!backgroundElement) return

      const backgroundRect = backgroundElement.getBoundingClientRect()
      squareMetricsRef.current = Array.from(
        backgroundElement.querySelectorAll<HTMLElement>('[data-square-background-cell]'),
        (element) => {
          const rect = element.getBoundingClientRect()

          return {
            element,
            proximity: 0,
            x: rect.left - backgroundRect.left + rect.width / 2,
            y: rect.top - backgroundRect.top + rect.height / 2,
          }
        },
      )
    }

    function resetSquares() {
      isActiveRef.current = false

      for (const square of squareMetricsRef.current) {
        square.proximity = 0
        square.element.style.setProperty('--square-proximity', '0')
      }

      backgroundRef.current?.classList.remove('is-active')
    }

    function handlePointerMove(event: PointerEvent) {
      if (event.pointerType === 'touch') return

      const backgroundElement = backgroundRef.current

      if (!backgroundElement) return

      const backgroundRect = backgroundElement.getBoundingClientRect()
      pointerMotionValuesRef.current.pointerX.set(event.clientX - backgroundRect.left)
      pointerMotionValuesRef.current.pointerY.set(event.clientY - backgroundRect.top)
      isActiveRef.current = true
      backgroundElement.classList.add('is-active')
    }

    function handlePointerLeave(event: MouseEvent) {
      if (event.relatedTarget !== null) return

      resetSquares()
    }

    measureSquares()
    window.addEventListener('pointermove', handlePointerMove, { passive: true })
    window.addEventListener('mouseout', handlePointerLeave)
    window.addEventListener('resize', measureSquares)
    window.addEventListener('blur', resetSquares)

    return () => {
      window.removeEventListener('pointermove', handlePointerMove)
      window.removeEventListener('mouseout', handlePointerLeave)
      window.removeEventListener('resize', measureSquares)
      window.removeEventListener('blur', resetSquares)
    }
  }, [])

  return {
    backgroundRef,
    squareCount: SQUARE_COUNT,
  }
}
