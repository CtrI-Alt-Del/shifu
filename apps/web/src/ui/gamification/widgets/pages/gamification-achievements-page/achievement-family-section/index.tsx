import { motion } from 'motion/react'

import type { Achievement, AchievementFamily } from '@/core/gamification/achievement'
import { ACHIEVEMENT_FAMILY_LABELS } from '@/ui/gamification/constants/achievement-presentation'

import { ENTRANCE_SECTION, ENTRANCE_STAGGER } from '@/constants/motion-variants'
import { AnimatedNumber } from '@/ui/shared/widgets/components/animated-number'

import { AchievementCard } from '../achievement-card'

export type AchievementFamilySectionProps = {
  family: AchievementFamily
  achievements: Achievement[]
  obtainedCount: number
}

export const AchievementFamilySection = ({
  family,
  achievements,
  obtainedCount,
}: AchievementFamilySectionProps) => (
  <motion.section
    aria-labelledby={`achievement-family-${family}`}
    className='grid gap-6 lg:grid-cols-[176px_minmax(0,1fr)] lg:gap-8'
    variants={ENTRANCE_SECTION}
  >
    <header className='space-y-2 lg:py-2'>
      <h3
        className='font-serif text-[26px] leading-tight'
        id={`achievement-family-${family}`}
      >
        {ACHIEVEMENT_FAMILY_LABELS[family]}
      </h3>
      <p className='text-[13px] text-muted-foreground'>
        <AnimatedNumber
          delay={0.2}
          format={(value) => `${value} de ${achievements.length} obtidas`}
          value={obtainedCount}
        />
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
