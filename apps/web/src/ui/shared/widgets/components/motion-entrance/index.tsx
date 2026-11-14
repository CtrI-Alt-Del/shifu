import { MotionConfig, motion } from 'motion/react'
import type { PropsWithChildren } from 'react'

import { ENTRANCE_STAGGER } from '@/constants/motion-variants'

import { useMotionEntrance } from './use-motion-entrance'

export type MotionEntranceProps = PropsWithChildren<{ className?: string }>

// Starts the entrance choreography for a page or a late-loading list.
// Descendants opt in by declaring `variants` from `@/constants/motion-variants`.
export const MotionEntrance = ({ children, className }: MotionEntranceProps) => {
  const { initial } = useMotionEntrance()

  return (
    <MotionConfig reducedMotion='user'>
      <motion.div
        animate='visible'
        className={className}
        initial={initial}
        variants={ENTRANCE_STAGGER}
      >
        {children}
      </motion.div>
    </MotionConfig>
  )
}
