import type { ReactNode } from 'react'

import { useMentorMascot } from './use-mentor-mascot'

export type MentorMascotProps = {
  className: string
  isAnimated: boolean
  fallback?: ReactNode
}

// Decorative: the text next to the mascot always carries the meaning.
export const MentorMascot = ({
  className,
  isAnimated,
  fallback = null,
}: MentorMascotProps) => {
  const { containerRef, hasFailed } = useMentorMascot({ isAnimated })

  if (hasFailed) return fallback

  return <div aria-hidden='true' ref={containerRef} className={className} />
}
