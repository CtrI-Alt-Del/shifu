import { useReducedMotion } from 'motion/react'
import { useEffect, useRef, useState } from 'react'

// Authored and previewed in the studio package; the web app serves that file.
import mentorMascotUrl from '@shifu/studio/scenes/mascot/scene-1?url'

export type UseMentorMascotOptions = {
  isAnimated: boolean
}

// Plays the mascot's greeting when it mounts, or shows the settled pose when it
// is static or motion is reduced. The player and the animation load on demand
// so they stay out of the main bundle.
export function useMentorMascot({ isAnimated }: UseMentorMascotOptions) {
  const containerRef = useRef<HTMLDivElement>(null)
  const prefersReducedMotion = useReducedMotion()
  const [hasFailed, setHasFailed] = useState(false)
  const shouldPlay = isAnimated && !prefersReducedMotion

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    let isMounted = true
    let destroyAnimation: (() => void) | undefined

    import('lottie-web/build/player/lottie_light')
      .then(({ default: lottie }) => {
        if (!isMounted) return
        const animation = lottie.loadAnimation({
          container,
          renderer: 'svg',
          loop: false,
          autoplay: shouldPlay,
          path: mentorMascotUrl,
        })
        animation.addEventListener('data_failed', () => setHasFailed(true))
        if (!shouldPlay) {
          animation.addEventListener('DOMLoaded', () =>
            animation.goToAndStop(animation.totalFrames - 1, true),
          )
        }
        destroyAnimation = () => animation.destroy()
      })
      .catch(() => {
        if (isMounted) setHasFailed(true)
      })

    return () => {
      isMounted = false
      destroyAnimation?.()
    }
  }, [shouldPlay])

  return { containerRef, hasFailed }
}
