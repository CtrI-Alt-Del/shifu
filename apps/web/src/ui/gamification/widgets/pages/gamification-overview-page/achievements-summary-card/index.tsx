import type { AchievementsSummary } from '@/core/gamification/overview'
import { motion } from 'motion/react'

import { ENTRANCE_SECTION, ENTRANCE_STAGGER } from '@/constants/motion-variants'
import { AnimatedNumber } from '@/ui/shared/widgets/components/animated-number'
import { Anchor } from '@/ui/shared/widgets/components/anchor'

import { RecentAchievementRow } from './recent-achievement-row'

export type AchievementsSummaryCardProps = {
  achievements: AchievementsSummary
}

export const AchievementsSummaryCard = ({
  achievements,
}: AchievementsSummaryCardProps) => (
  <motion.section
    aria-labelledby='gamification-overview-achievements-title'
    className='space-y-2 border-t border-border pt-6'
    variants={ENTRANCE_SECTION}
  >
    <div className='flex flex-wrap items-center justify-between gap-3'>
      <div className='flex flex-wrap items-center gap-4'>
        <h3
          className='font-serif text-[28px] leading-tight'
          id='gamification-overview-achievements-title'
        >
          Conquistas recentes
        </h3>
        <p className='text-[13px] text-muted-foreground'>
          <AnimatedNumber delay={0.5} value={achievements.obtainedCount} /> de{' '}
          {achievements.catalogCount} obtidas
        </p>
      </div>
      <Anchor
        className='inline-flex min-h-11 items-center justify-center rounded-md px-4 font-semibold text-muted-foreground transition-colors hover:bg-white/5 hover:text-foreground'
        route='gamificationAchievements'
      >
        Ver todas as conquistas
      </Anchor>
    </div>

    {achievements.recent.length > 0 ? (
      <motion.ul aria-label='Conquistas recentes' variants={ENTRANCE_STAGGER}>
        {achievements.recent.map((achievement) => (
          <RecentAchievementRow
            achievement={achievement}
            key={achievement.achievementId}
          />
        ))}
      </motion.ul>
    ) : (
      <p className='py-3 text-muted-foreground'>
        Você ainda não obteve conquistas. Continue praticando para desbloquear as
        primeiras.
      </p>
    )}
  </motion.section>
)
