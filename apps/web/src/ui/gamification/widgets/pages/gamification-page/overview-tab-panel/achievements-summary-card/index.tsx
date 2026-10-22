import type { AchievementsSummary } from '@/core/gamification/overview'
import { Button } from '@/ui/shadcn/button'

import { RecentAchievementRow } from './recent-achievement-row'

export type AchievementsSummaryCardProps = {
  achievements: AchievementsSummary
  onViewAchievements: () => void
}

export const AchievementsSummaryCard = ({
  achievements,
  onViewAchievements,
}: AchievementsSummaryCardProps) => (
  <section
    aria-labelledby='gamification-overview-achievements-title'
    className='space-y-5 rounded-[14px] border border-border bg-card p-6'
  >
    <div className='flex flex-wrap items-baseline justify-between gap-2'>
      <h3 className='font-serif text-2xl' id='gamification-overview-achievements-title'>
        Suas conquistas
      </h3>
      <p className='text-sm text-muted-foreground'>
        <span className='text-latao-text'>{achievements.obtainedCount}</span> de{' '}
        <span className='text-latao-text'>{achievements.catalogCount}</span> obtidas
      </p>
    </div>

    {achievements.recent.length > 0 ? (
      <ul aria-label='Conquistas recentes'>
        {achievements.recent.map((achievement) => (
          <RecentAchievementRow
            achievement={achievement}
            key={achievement.achievementId}
          />
        ))}
      </ul>
    ) : (
      <p className='text-muted-foreground'>
        Você ainda não obteve conquistas. Continue praticando para desbloquear as
        primeiras.
      </p>
    )}

    <Button onClick={onViewAchievements} type='button' variant='ghost'>
      Ver todas as conquistas
    </Button>
  </section>
)
