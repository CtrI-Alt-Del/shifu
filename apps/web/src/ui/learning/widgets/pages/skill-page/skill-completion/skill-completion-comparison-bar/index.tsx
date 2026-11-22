import { motion } from 'motion/react'

import { ENTRANCE_FILL } from '@/constants/motion-variants'

export type SkillCompletionComparisonBarProps = {
  startingPercent: number
  gainPercent: number
  unknownPercent: number
  className?: string
}

export const SkillCompletionComparisonBar = ({
  startingPercent,
  gainPercent,
  unknownPercent,
  className = '',
}: SkillCompletionComparisonBarProps) => {
  return (
    <span
      aria-hidden='true'
      className={`relative block h-2 w-full overflow-hidden rounded-full bg-muted ${className}`}
    >
      {startingPercent > 0 ? (
        <motion.span
          className='absolute inset-y-0 left-0 bg-jade-fill'
          custom={startingPercent}
          variants={ENTRANCE_FILL}
        />
      ) : null}
      {gainPercent > 0 ? (
        <motion.span
          className='absolute inset-y-0 bg-jade-text'
          custom={gainPercent}
          style={{ left: `${startingPercent}%` }}
          variants={ENTRANCE_FILL}
        />
      ) : null}
      {unknownPercent > 0 ? (
        <motion.span
          className='absolute inset-y-0 left-0 bg-muted-foreground'
          custom={unknownPercent}
          variants={ENTRANCE_FILL}
        />
      ) : null}
    </span>
  )
}
