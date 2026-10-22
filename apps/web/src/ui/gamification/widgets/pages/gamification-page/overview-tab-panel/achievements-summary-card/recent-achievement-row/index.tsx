import type { RecentAchievement } from '@/core/gamification/overview'
import { useFormatDate } from '@/ui/shared/hooks/use-format-date'
import { Icon } from '@/ui/shared/widgets/components/icon'

export type RecentAchievementRowProps = {
  achievement: RecentAchievement
}

export const RecentAchievementRow = ({ achievement }: RecentAchievementRowProps) => {
  const { formatShortDate } = useFormatDate()
  const achievedOn = formatShortDate(achievement.achievedAt)

  return (
    <li
      aria-label={`${achievement.name}, ${achievement.criterionLabel}, +${achievement.xpReward} XP, em ${achievedOn}`}
      className='flex items-center gap-4 border-b border-border py-4 last:border-b-0'
    >
      <span className='grid size-9 shrink-0 place-items-center rounded-[10px] bg-latao-tint text-latao-text'>
        <Icon name='trophy' size={18} />
      </span>

      <span className='min-w-0 flex-1'>
        <span className='block truncate text-[15px]'>{achievement.name}</span>
        <span className='block text-[13px] text-muted-foreground'>
          {achievement.criterionLabel}
        </span>
      </span>

      <span className='shrink-0 text-right'>
        <span className='block text-[15px] text-latao-text'>
          +{achievement.xpReward} XP
        </span>
        <span className='block text-[13px] text-muted-foreground'>{achievedOn}</span>
      </span>
    </li>
  )
}
