import { motion } from 'motion/react'

import type { Achievement } from '@/core/gamification/achievement'

import { ENTRANCE_SECTION, ENTRANCE_STAGGER } from '@/constants/motion-variants'

import { AchievementCard } from '../achievement-card'

export type HistoricalAchievementsSectionProps = {
  achievements: Achievement[]
}

export const HistoricalAchievementsSection = ({
  achievements,
}: HistoricalAchievementsSectionProps) => (
  <motion.section
    aria-labelledby='achievement-family-historico'
    className='grid gap-6 lg:grid-cols-[176px_minmax(0,1fr)] lg:gap-8'
    variants={ENTRANCE_SECTION}
  >
    <header className='space-y-2 lg:py-2'>
      <h3
        className='font-serif text-[26px] leading-tight'
        id='achievement-family-historico'
      >
        Histórico
      </h3>
      <p className='text-[13px] leading-normal text-muted-foreground'>
        Conquistas retiradas do catálogo, visíveis apenas para quem já as obteve.
      </p>
    </header>
    <motion.div
      className='grid gap-6 sm:grid-cols-2 xl:grid-cols-3'
      variants={ENTRANCE_STAGGER}
    >
      {achievements.map((achievement) => (
        <AchievementCard achievement={achievement} key={achievement.code} />
      ))}
    </motion.div>
  </motion.section>
)
