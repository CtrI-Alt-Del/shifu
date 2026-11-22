import { Button } from '@/ui/shadcn/button'
import { Icon } from '@/ui/shared/widgets/components/icon'
import { MotionEntrance } from '@/ui/shared/widgets/components/motion-entrance'

import { MonthCalendarCard } from './month-calendar-card'
import { RecentAchievementsCard } from './recent-achievements-card'
import { useEngagementPanelSection } from './use-engagement-panel-section'
import { WeeklyXpCard } from './weekly-xp-card'

export const EngagementPanelSection = () => {
  const {
    state,
    monthLabel,
    monthDays,
    recentAchievements,
    nextAchievement,
    weeklyXp,
    isRetrying,
    handleRetry,
  } = useEngagementPanelSection()

  return (
    <section aria-labelledby='engagement-section-title' className='space-y-4'>
      <h2
        className='flex items-center gap-2.5 pt-2 text-lg font-semibold'
        id='engagement-section-title'
      >
        <span aria-hidden='true' className='size-2.5 rounded-full bg-latao-fill' />
        Engajamento
      </h2>

      {state === 'loading' ? (
        <output
          aria-busy='true'
          aria-label='Carregando seu engajamento'
          className='block space-y-4'
        >
          <div className='grid gap-4 lg:grid-cols-2'>
            <div
              aria-hidden='true'
              className='h-80 animate-pulse rounded-[14px] border border-border bg-surface-alt'
            />
            <div
              aria-hidden='true'
              className='h-80 animate-pulse rounded-[14px] border border-border bg-surface-alt'
            />
          </div>
          <div
            aria-hidden='true'
            className='h-72 animate-pulse rounded-[14px] border border-border bg-surface-alt'
          />
        </output>
      ) : null}

      {state === 'error' ? (
        <div
          aria-labelledby='engagement-section-error-title'
          className='flex flex-col items-start gap-3 rounded-[14px] border border-border bg-surface-alt p-6'
          role='alert'
        >
          <h3
            className='flex items-center gap-2 font-semibold'
            id='engagement-section-error-title'
          >
            <Icon className='text-selo-text' name='circle-alert' size={18} />
            Não foi possível carregar seu engajamento
          </h3>
          <p className='text-[13px] text-muted-foreground'>
            Seu XP, sua sequência e suas conquistas continuam salvos. Tente novamente em
            alguns instantes.
          </p>
          <Button disabled={isRetrying} onClick={handleRetry} type='button'>
            Tentar novamente
          </Button>
        </div>
      ) : null}

      {state === 'success' ? (
        <MotionEntrance className='space-y-4'>
          <div className='grid gap-4 lg:grid-cols-2'>
            <MonthCalendarCard days={monthDays} monthLabel={monthLabel} />
            <RecentAchievementsCard
              achievements={recentAchievements}
              nextAchievement={nextAchievement}
            />
          </div>
          <WeeklyXpCard weeks={weeklyXp} />
        </MotionEntrance>
      ) : null}
    </section>
  )
}
