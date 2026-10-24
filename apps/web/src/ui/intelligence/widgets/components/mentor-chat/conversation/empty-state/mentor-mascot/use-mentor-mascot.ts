import { useReducedMotion } from 'motion/react'
import { useEffect, useRef, useState } from 'react'

// Authored and previewed in the studio package; the web app serves that file.
import mentorMascotUrl from '@shifu/studio/scenes/mascot/scene-1?url'

// Plays the mascot's greeting each time the empty conversation mounts. The
// player and the animation load on demand so they stay out of the main bundle.
export function useMentorMascot() {
  const containerRef = useRef<HTMLDivElement>(null)
  const prefersReducedMotion = useReducedMotion()
  const [hasFailed, setHasFailed] = useState(false)

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
          autoplay: !prefersReducedMotion,
          path: mentorMascotUrl,
        })
        animation.addEventListener('data_failed', () => setHasFailed(true))
        if (prefersReducedMotion) {
          // Show the settled mascot without the entrance.
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
  }, [prefersReducedMotion])

  return { containerRef, hasFailed }
}
