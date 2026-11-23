import { motion } from 'motion/react'

import { ENTRANCE_CARD } from '@/constants/motion-variants'
import { Button } from '@/ui/shadcn/button'
import { Skeleton } from '@/ui/shadcn/skeleton'
import { AnimatedNumber } from '@/ui/shared/widgets/components/animated-number'
import { MotionEntrance } from '@/ui/shared/widgets/components/motion-entrance'

import { useLearningPanoramaSummary } from './use-learning-panorama-summary'

const CARD_CLASS_NAME =
  'flex min-w-0 flex-col gap-2 rounded-[14px] border border-border bg-surface-alt p-5'
const MARKER_LABEL_CLASS_NAME =
  'flex items-center gap-2 text-xs font-medium text-muted-foreground'

// Renders the two Aprendizagem summary cards as direct grid items of the
// panel's summary grid, which is why every state wraps them without a box.
export const LearningPanoramaSummary = () => {
  const { state, cards, isRetrying, formatCount, handleRetry } =
    useLearningPanoramaSummary()

  if (state === 'loading') {
    return (
      <>
        {cards.map((card) => (
          <output
            aria-busy='true'
            aria-label={`Carregando ${card.caption}`}
            className={`${CARD_CLASS_NAME} block`}
            key={card.key}
          >
            <Skeleton aria-hidden='true' className='h-3 w-24' />
            <Skeleton aria-hidden='true' className='mt-3 h-8 w-16' />
            <Skeleton aria-hidden='true' className='mt-2 h-4 w-40' />
          </output>
        ))}
      </>
    )
  }

  if (state === 'error') {
    return (
      <>
        {cards.map((card) => (
          <article className={CARD_CLASS_NAME} key={card.key}>
            <p className={MARKER_LABEL_CLASS_NAME}>
              <span aria-hidden='true' className='size-2 rounded-full bg-jade-fill' />
              Aprendizagem
            </p>
            <p className='text-[13px] text-secondary-foreground'>{card.caption}</p>
            <p className='text-sm text-foreground' role='alert'>
              Indisponível no momento.
            </p>
            <Button
              className='mt-1 self-start'
              disabled={isRetrying}
              onClick={handleRetry}
              type='button'
              variant='outline'
            >
              Tentar novamente
            </Button>
          </article>
        ))}
      </>
    )
  }

  return (
    <MotionEntrance className='contents'>
      {cards.map((card) => (
        <motion.article
          aria-labelledby={`learning-panorama-summary-${card.key}`}
          className={CARD_CLASS_NAME}
          key={card.key}
          variants={ENTRANCE_CARD}
        >
          <p className={MARKER_LABEL_CLASS_NAME}>
            <span aria-hidden='true' className='size-2 rounded-full bg-jade-fill' />
            Aprendizagem
          </p>
          <p className='font-mono text-[28px] leading-tight font-semibold text-foreground'>
            <AnimatedNumber format={formatCount} value={card.value} />
          </p>
          <p
            className='text-[13px] text-secondary-foreground'
            id={`learning-panorama-summary-${card.key}`}
          >
            {card.caption}
          </p>
        </motion.article>
      ))}
    </MotionEntrance>
  )
}
