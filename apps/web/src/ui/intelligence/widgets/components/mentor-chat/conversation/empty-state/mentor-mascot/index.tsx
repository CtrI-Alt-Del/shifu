import { motion } from 'motion/react'

import { ENTRANCE_POP } from '@/constants/motion-variants'
import { Icon } from '@/ui/shared/widgets/components/icon'

import { useMentorMascot } from './use-mentor-mascot'

export type MentorMascotProps = { surface: 'page' | 'fab' }

export const MentorMascot = ({ surface }: MentorMascotProps) => {
  const { containerRef, hasFailed } = useMentorMascot()

  // Without the animation the greeting falls back to the plain Mentor icon.
  if (hasFailed) {
    return (
      <motion.span
        className={`mx-auto grid place-items-center rounded-full bg-jade-tint text-jade-text ${surface === 'fab' ? 'size-11' : 'size-14'}`}
        variants={ENTRANCE_POP}
      >
        <Icon name='message-circle' className={surface === 'fab' ? 'size-5' : 'size-6'} />
      </motion.span>
    )
  }

  // Decorative: the heading and text below carry the message.
  return (
    <div
      aria-hidden='true'
      ref={containerRef}
      className={`mx-auto ${surface === 'fab' ? 'size-28' : 'size-40'}`}
    />
  )
}
