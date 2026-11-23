import { motion } from 'motion/react'

import {
  ENTRANCE_CARD,
  ENTRANCE_FILL,
  ENTRANCE_MEDAL,
  ENTRANCE_ROW,
  ENTRANCE_STAGGER,
} from '@/constants/motion-variants'
import { Anchor } from '@/ui/shared/widgets/components/anchor'
import { Icon } from '@/ui/shared/widgets/components/icon'

import type {
  NextAchievementView,
  RecentAchievementView,
} from '../use-engagement-panel-section'

export type RecentAchievementsCardProps = {
  achievements: RecentAchievementView[]
  nextAchievement: NextAchievementView | null
}

export const RecentAchievementsCard = ({
  achievements,
  nextAchievement,
}: RecentAchievementsCardProps) => (
  <motion.article
    aria-labelledby='engagement-achievements-title'
    className='space-y-4 rounded-[14px] border border-border bg-surface-alt p-5'
    variants={ENTRANCE_CARD}
  >
    <div className='flex flex-wrap items-center justify-between gap-x-3'>
      <h3 className='font-semibold' id='engagement-achievements-title'>
        Conquistas recentes
      </h3>
      <Anchor
        aria-label='Ver todas as conquistas'
        className='inline-flex min-h-11 items-center text-sm font-medium text-secondary-foreground underline underline-offset-2 hover:text-foreground lg:min-h-0'
        route='gamificationAchievements'
      >
        Ver todas
      </Anchor>
    </div>

    {achievements.length > 0 ? (
      <motion.ul
        aria-label='Conquistas recentes'
        className='space-y-3'
        variants={ENTRANCE_STAGGER}
      >
        {achievements.map((achievement) => (
          <motion.li
            className='flex items-center gap-3'
            key={achievement.id}
            variants={ENTRANCE_ROW}
          >
            <motion.span
              className='grid size-9 shrink-0 place-items-center rounded-md bg-latao-tint text-latao-solid'
              variants={ENTRANCE_MEDAL}
            >
              <Icon name={achievement.icon} size={18} />
            </motion.span>
            <span className='min-w-0 flex-1'>
              <span className='block truncate text-sm font-semibold'>
                {achievement.name}
              </span>
              <span className='block text-[13px] text-muted-foreground'>
                {achievement.criterionLabel} · {achievement.achievedOn}
              </span>
            </span>
            <span className='shrink-0 font-mono text-sm font-semibold text-latao-text'>
              {achievement.xpLabel}
            </span>
          </motion.li>
        ))}
      </motion.ul>
    ) : (
      <p className='text-[13px] text-muted-foreground'>
        Você ainda não obteve conquistas. Continue praticando para desbloquear as
        primeiras.
      </p>
    )}

    {nextAchievement ? (
      <section
        aria-labelledby='engagement-next-achievement-title'
        className='space-y-2 border-t border-border pt-4'
      >
        <p
          className='text-xs font-medium text-muted-foreground'
          id='engagement-next-achievement-title'
        >
          Próxima conquista
        </p>
        <div className='flex items-baseline justify-between gap-3'>
          <p className='text-sm font-semibold'>
            {nextAchievement.name} · {nextAchievement.criterionLabel}
          </p>
          <p className='shrink-0 font-mono text-sm font-semibold text-secondary-foreground'>
            {nextAchievement.progressLabel}
          </p>
        </div>
        <div
          aria-label={`Progresso para ${nextAchievement.name}`}
          aria-valuemax={100}
          aria-valuemin={0}
          aria-valuenow={nextAchievement.progressPercentage}
          aria-valuetext={nextAchievement.progressLabel}
          className='h-2 w-full overflow-hidden rounded-sm bg-muted'
          role='progressbar'
        >
          <motion.div
            className='h-full bg-latao-fill'
            custom={nextAchievement.progressPercentage}
            variants={ENTRANCE_FILL}
          />
        </div>
        <p className='text-[13px] text-muted-foreground'>{nextAchievement.hint}</p>
      </section>
    ) : null}
  </motion.article>
)
