import { motion } from 'motion/react'

import { ENTRANCE_FILL_TRANSITION } from '@/constants/motion-variants'
import { AnimatedNumber } from '@/ui/shared/widgets/components/animated-number'

import { useProgressMeter } from './use-progress-meter'

export type ProgressMeterProps = {
  label?: string
  compact?: boolean
  tone?: 'primary' | 'success'
  value: number
}

export const ProgressMeter = (props: ProgressMeterProps) => {
  const { label, compact = false } = props
  const { boundedValue, displayValue, toneClassName, fillClassName, fillInitial } =
    useProgressMeter(props)

  return (
    <div>
      {label ? (
        <div
          className={
            compact ? 'sr-only' : 'mb-2 flex items-center justify-between gap-4 text-sm'
          }
        >
          <span className='font-semibold text-foreground'>{label}</span>
          <AnimatedNumber
            className={`font-bold ${toneClassName}`}
            delay={0.2}
            format={(current) => `${current}%`}
            value={displayValue}
          />
        </div>
      ) : null}
      {/* aria values report the final figure at once; only the drawing grows. */}
      <div
        aria-label={label}
        aria-valuemax={100}
        aria-valuemin={0}
        aria-valuenow={boundedValue}
        aria-valuetext={`${displayValue}%`}
        className={`${compact ? 'h-1' : 'h-2.5'} overflow-hidden rounded-full bg-muted`}
        role='progressbar'
      >
        <motion.div
          animate={{ width: `${boundedValue}%` }}
          className={`h-full rounded-full ${fillClassName}`}
          initial={fillInitial}
          transition={ENTRANCE_FILL_TRANSITION}
        />
      </div>
    </div>
  )
}
