import type { StreakOverview } from '@/core/gamification/overview'
import { motion } from 'motion/react'

import { ENTRANCE_SECTION } from '@/constants/motion-variants'
import { AnimatedNumber } from '@/ui/shared/widgets/components/animated-number'
import { Icon } from '@/ui/shared/widgets/components/icon'

import { PracticeWeekStrip } from './practice-week-strip'

export type StreakSummaryCardProps = {
  streak: StreakOverview
}

export const StreakSummaryCard = ({ streak }: StreakSummaryCardProps) => (
  <motion.section
    aria-labelledby='gamification-overview-streak-title'
    className='flex flex-col gap-4 rounded-[10px] bg-card p-6'
    variants={ENTRANCE_SECTION}
  >
    <h3
      className='flex items-center gap-2 font-medium'
      id='gamification-overview-streak-title'
    >
      <motion.span
        animate={{ scale: [1, 1.18, 1] }}
        className='inline-flex'
        transition={{ duration: 0.6, delay: 0.5, ease: 'easeOut' }}
      >
        <Icon className='text-latao-solid' name='flame' size={20} />
      </motion.span>
      Constância
    </h3>

    <div className='flex items-center justify-between gap-4'>
      <p className='flex items-center gap-2'>
        <AnimatedNumber
          className='font-serif text-5xl leading-none text-latao-text'
          delay={0.3}
          value={streak.streak.current}
        />
        <span className='max-w-[4.5rem] text-sm leading-[1.4] text-secondary-foreground'>
          {streak.streak.current === 1 ? 'dia seguido' : 'dias seguidos'}
        </span>
      </p>
      <p className='text-[13px] text-secondary-foreground'>
        Recorde: <AnimatedNumber delay={0.4} value={streak.streak.longest} />{' '}
        {streak.streak.longest === 1 ? 'dia' : 'dias'}
      </p>
    </div>

    <PracticeWeekStrip days={streak.lastSevenDays} today={streak.today} />

    <p className='text-xs text-secondary-foreground'>
      {streak.isTodayPending
        ? 'Pratique hoje para manter a sequência.'
        : 'Você já praticou hoje.'}
    </p>
  </motion.section>
)
