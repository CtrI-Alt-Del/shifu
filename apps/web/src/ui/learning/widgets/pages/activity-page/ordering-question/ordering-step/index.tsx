import { motion } from 'motion/react'

import type { OrderingQuestion } from '@/core/learning/choice-activity'
import { ENTRANCE_RISE } from '@/constants/motion-variants'
import { Button } from '@/ui/shadcn/button'
import { Icon } from '@/ui/shared/widgets/components/icon'

import { useOrderingStep } from './use-ordering-step'

export type OrderingStepProps = {
  disabled: boolean
  isFirst: boolean
  isLast: boolean
  isVerified: boolean
  // Changes only on button moves, so drag reorders keep the sortable transition alone.
  moveCount: number
  onMove: (stepKey: string, offset: -1 | 1) => void
  position: number
  step: OrderingQuestion['steps'][number]
}

export const OrderingStep = (props: OrderingStepProps) => {
  const { disabled, isFirst, isLast, isVerified, moveCount, onMove, position, step } =
    props
  const { isDragging, listeners, prefersReducedMotion, style, setNodeRef } =
    useOrderingStep(props)

  return (
    <motion.li
      layout={prefersReducedMotion ? false : 'position'}
      layoutDependency={moveCount}
      transition={{ layout: { duration: 0.22, ease: [0.22, 1, 0.36, 1] } }}
      variants={ENTRANCE_RISE}
    >
      <div
        className='relative flex min-h-14 items-center gap-3 rounded-md border border-control-border bg-card p-2 data-[dragging=true]:z-10 data-[dragging=true]:shadow-lg data-[draggable=true]:cursor-grab data-[dragging=true]:cursor-grabbing sm:p-3'
        data-draggable={!disabled && !isVerified}
        data-dragging={isDragging}
        ref={setNodeRef}
        style={style}
        {...(isVerified ? {} : listeners)}
      >
        {!isVerified ? (
          <Icon
            aria-hidden='true'
            className='shrink-0 text-muted-foreground'
            name='grip-vertical'
            size={16}
          />
        ) : null}
        <span
          aria-hidden='true'
          className='w-7 shrink-0 text-center font-mono text-sm text-muted-foreground'
        >
          {position}
        </span>
        <span className='min-w-0 flex-1 whitespace-pre-wrap text-sm'>{step.text}</span>
        {!isVerified ? (
          <span className='flex shrink-0 gap-1'>
            <Button
              aria-label={`Mover para cima: ${step.text}`}
              className='h-11 w-11 min-h-11 px-0'
              disabled={disabled || isFirst}
              onClick={() => onMove(step.key, -1)}
              type='button'
              variant='outline'
            >
              <Icon name='arrow-up' size={18} />
            </Button>
            <Button
              aria-label={`Mover para baixo: ${step.text}`}
              className='h-11 w-11 min-h-11 px-0'
              disabled={disabled || isLast}
              onClick={() => onMove(step.key, 1)}
              type='button'
              variant='outline'
            >
              <Icon className='rotate-180' name='arrow-up' size={18} />
            </Button>
          </span>
        ) : null}
      </div>
    </motion.li>
  )
}
