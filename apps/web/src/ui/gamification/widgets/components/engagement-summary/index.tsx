import { motion } from 'motion/react'

import { ENTRANCE_CARD, ENTRANCE_FILL } from '@/constants/motion-variants'
import { Button } from '@/ui/shadcn/button'
import { AnimatedNumber } from '@/ui/shared/widgets/components/animated-number'
import { MotionEntrance } from '@/ui/shared/widgets/components/motion-entrance'

import { useEngagementSummary } from './use-engagement-summary'

const UNAVAILABLE_CARDS = ['Nível e XP', 'Sequência de prática'] as const

const CARD_CLASS_NAME = 'space-y-2 rounded-[14px] border border-border bg-surface-alt p-5'

// Renders the two Engajamento summary cards as grid cells of the panel
// layout's summary row, so every root below is a card or a `contents` wrapper.
export const EngagementSummary = () => {
  const { summary, state, isRetrying, formatXp, handleRetry } = useEngagementSummary()

  if (state === 'loading') {
    return (
      <>
        <output
          aria-busy='true'
          aria-label='Carregando nível e XP'
          className={`block ${CARD_CLASS_NAME}`}
        >
          <div aria-hidden='true' className='h-4 w-24 animate-pulse rounded bg-muted' />
          <div aria-hidden='true' className='h-8 w-32 animate-pulse rounded bg-muted' />
          <div aria-hidden='true' className='h-4 w-full animate-pulse rounded bg-muted' />
        </output>
        <output
          aria-busy='true'
          aria-label='Carregando sequência'
          className={`block ${CARD_CLASS_NAME}`}
        >
          <div aria-hidden='true' className='h-4 w-24 animate-pulse rounded bg-muted' />
          <div aria-hidden='true' className='h-8 w-32 animate-pulse rounded bg-muted' />
          <div aria-hidden='true' className='h-4 w-full animate-pulse rounded bg-muted' />
        </output>
      </>
    )
  }

  if (state === 'error' || !summary) {
    return (
      <>
        {UNAVAILABLE_CARDS.map((caption) => (
          <article className={CARD_CLASS_NAME} key={caption}>
            <p className='flex items-center gap-2 text-xs font-medium text-muted-foreground'>
              <span aria-hidden='true' className='size-2 rounded-full bg-latao-fill' />
              Engajamento
            </p>
            <p className='text-[13px] text-secondary-foreground'>{caption}</p>
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
      <motion.article
        aria-label='Engajamento: nível e XP'
        className={CARD_CLASS_NAME}
        variants={ENTRANCE_CARD}
      >
        <p className='flex items-center gap-2 text-xs font-medium text-muted-foreground'>
          <span aria-hidden='true' className='size-2 rounded-full bg-latao-fill' />
          Engajamento
        </p>
        <AnimatedNumber
          className='block font-mono text-[28px] leading-tight font-semibold'
          format={(value) => `Nível ${value}`}
          value={summary.level}
        />
        <p className='text-[13px] text-secondary-foreground'>
          {formatXp(summary.totalXp)} XP · faltam {formatXp(summary.xpForNextLevel)} XP
          para o nível {summary.level + 1}
        </p>
        {/* The fill is decorative: XP total, remaining XP and the next level are
          all text, so the bar is never the only carrier (RP-13). */}
        <div
          aria-label={`Progresso para o nível ${summary.level + 1}`}
          aria-valuemax={100}
          aria-valuemin={0}
          aria-valuenow={summary.levelPercentage}
          aria-valuetext={`${summary.levelPercentage}% concluído, faltam ${formatXp(summary.xpForNextLevel)} XP`}
          className='h-2 w-full overflow-hidden rounded-sm bg-muted'
          role='progressbar'
        >
          <motion.div
            className='h-full bg-latao-fill'
            custom={summary.levelPercentage}
            variants={ENTRANCE_FILL}
          />
        </div>
      </motion.article>

      <motion.article
        aria-label='Engajamento: sequência'
        className={CARD_CLASS_NAME}
        variants={ENTRANCE_CARD}
      >
        <p className='flex items-center gap-2 text-xs font-medium text-muted-foreground'>
          <span aria-hidden='true' className='size-2 rounded-full bg-latao-fill' />
          Engajamento
        </p>
        <AnimatedNumber
          className='block font-mono text-[28px] leading-tight font-semibold'
          format={(value) => `${value} ${value === 1 ? 'dia' : 'dias'}`}
          value={summary.currentStreak}
        />
        <p className='text-[13px] text-secondary-foreground'>
          Sequência atual · recorde de {summary.longestStreak}{' '}
          {summary.longestStreak === 1 ? 'dia' : 'dias'}
        </p>
      </motion.article>
    </MotionEntrance>
  )
}
