import { motion } from 'motion/react'

import type { RecentAchievement } from '@/core/gamification/overview'
import { ACHIEVEMENT_CODE_ICONS } from '@/ui/gamification/constants/achievement-presentation'
import { ENTRANCE_ROW, ENTRANCE_MEDAL } from '@/constants/motion-variants'
import { useFormatDate } from '@/ui/shared/hooks/use-format-date'
import { Icon } from '@/ui/shared/widgets/components/icon'

export type RecentAchievementRowProps = {
  achievement: RecentAchievement
}

export const RecentAchievementRow = ({ achievement }: RecentAchievementRowProps) => {
  const { formatShortDate } = useFormatDate()
  const achievedOn = formatShortDate(achievement.achievedAt)

  return (
    <motion.li
      aria-label={`${achievement.name}, ${achievement.criterionLabel}, +${achievement.xpReward} XP, em ${achievedOn}`}
      className='flex items-center gap-6 border-b border-border py-3'
      variants={ENTRANCE_ROW}
    >
      <span className='flex min-w-0 flex-1 items-center gap-3'>
        <motion.span
          className='grid size-12 shrink-0 place-items-center rounded-[10px] bg-latao-tint text-latao-solid'
          variants={ENTRANCE_MEDAL}
        >
          <Icon
            name={ACHIEVEMENT_CODE_ICONS[achievement.achievementId] ?? 'trophy'}
            size={24}
          />
        </motion.span>
        <span className='min-w-0 flex-1 space-y-1'>
          <span className='block truncate font-semibold'>{achievement.name}</span>
          <span className='block text-[13px] leading-normal text-secondary-foreground'>
            {achievement.criterionLabel}
          </span>
        </span>
        <span className='shrink-0 font-mono text-sm font-semibold text-latao-solid'>
          +{achievement.xpReward} XP
        </span>
      </span>
      <span className='shrink-0 text-[13px] text-muted-foreground'>{achievedOn}</span>
    </motion.li>
  )
}
