import { motion } from 'motion/react'

import type { Achievement } from '@/core/gamification/achievement'
import { ENTRANCE_CARD, ENTRANCE_FILL, ENTRANCE_MEDAL } from '@/constants/motion-variants'
import { Icon } from '@/ui/shared/widgets/components/icon'

import { useAchievementCard } from './use-achievement-card'

export type AchievementCardProps = {
  achievement: Achievement
}

export const AchievementCard = (props: AchievementCardProps) => {
  const { achievement } = props
  const { isLocked, criterion, medalIcon, statusIcon, statusLabel, progressPercentage } =
    useAchievementCard(props)

  return (
    <motion.article
      className='flex min-h-[200px] flex-col gap-3 rounded-[10px] bg-card p-4'
      variants={ENTRANCE_CARD}
      whileHover={{ y: -3 }}
    >
      <div className='flex gap-3'>
        <motion.span
          className={`grid size-10 shrink-0 place-items-center rounded-[10px] ${isLocked ? 'bg-muted text-muted-foreground' : 'bg-latao-tint text-latao-solid'}`}
          variants={isLocked ? undefined : ENTRANCE_MEDAL}
        >
          <Icon name={medalIcon} size={20} />
        </motion.span>
        <div className='min-w-0 space-y-1'>
          <h4 className='font-semibold'>{achievement.name}</h4>
          <p className='text-[13px] leading-normal text-secondary-foreground'>
            {criterion}
          </p>
        </div>
      </div>

      <p className='mt-auto flex items-center justify-between gap-3'>
        <span className='text-xs text-muted-foreground'>Recompensa</span>
        <span className='font-mono text-sm text-latao-text'>
          +{achievement.xpReward} XP
        </span>
      </p>

      <div className='space-y-2'>
        <p
          className={`flex items-center gap-2 text-xs leading-normal ${isLocked ? 'text-muted-foreground' : 'text-secondary-foreground'}`}
        >
          <Icon
            className={isLocked ? 'text-muted-foreground' : 'text-latao-solid'}
            name={statusIcon}
            size={14}
          />
          {statusLabel}
        </p>
        {/* The bar repeats the textual progress above, so it is decorative and
          the fill is never the only carrier of the milestone (RP-13). */}
        {progressPercentage !== null ? (
          <div aria-hidden='true' className='h-2 overflow-hidden rounded-full bg-muted'>
            <motion.div
              className='h-full rounded-full bg-latao-fill'
              custom={progressPercentage}
              variants={ENTRANCE_FILL}
            />
          </div>
        ) : null}
      </div>
    </motion.article>
  )
}
