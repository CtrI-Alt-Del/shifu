import type { Achievement } from '@/core/gamification/achievement'
import { Button } from '@/ui/shadcn/button'
import { Icon } from '@/ui/shared/widgets/components/icon'

import { AchievementFamilySection } from '../achievement-family-section'
import { HistoricalAchievementsSection } from '../historical-achievements-section'
import { ProfileSummaryCard } from '../profile-summary-card'
import type {
  AchievementFamilyGroup,
  GamificationPageState,
  ProfileSummary,
} from '../use-gamification-page'

export type AchievementsTabPanelProps = {
  state: GamificationPageState
  profileSummary: ProfileSummary | null
  familyGroups: AchievementFamilyGroup[]
  historicalAchievements: Achievement[]
  isRetrying: boolean
  onRetry: () => void
}

export const AchievementsTabPanel = ({
  state,
  profileSummary,
  familyGroups,
  historicalAchievements,
  isRetrying,
  onRetry,
}: AchievementsTabPanelProps) => {
  if (state === 'loading') {
    return (
      <output
        aria-busy='true'
        aria-label='Carregando conquistas'
        className='block space-y-5 rounded-lg border border-border bg-card p-6'
      >
        <div aria-hidden='true' className='h-32 w-full animate-pulse rounded bg-muted' />
        <div aria-hidden='true' className='h-64 animate-pulse rounded bg-muted' />
        <span className='sr-only'>Carregando conquistas</span>
      </output>
    )
  }

  if (state === 'error') {
    return (
      <section
        aria-labelledby='gamification-error-title'
        className='rounded-lg border border-border bg-card p-8 text-center'
        role='alert'
      >
        <Icon className='mx-auto text-selo-text' name='circle-alert' size={32} />
        <h2
          autoFocus
          className='mt-4 font-serif text-2xl'
          id='gamification-error-title'
          tabIndex={-1}
        >
          Não foi possível carregar suas conquistas
        </h2>
        <p className='mt-3 text-muted-foreground'>Tente novamente em alguns instantes.</p>
        <Button className='mt-6' disabled={isRetrying} onClick={onRetry} type='button'>
          Tentar novamente
        </Button>
      </section>
    )
  }

  if (state === 'empty') {
    return (
      <section className='flex min-h-[320px] flex-col items-center justify-center rounded-[10px] border border-border bg-surface-alt p-8 text-center'>
        <span className='flex size-12 items-center justify-center rounded-full bg-muted'>
          <Icon className='text-foreground/80' name='trophy' size={22} />
        </span>
        <h2 className='mt-4 text-xl font-semibold'>Nenhuma conquista disponível ainda</h2>
        <p className='mt-4 max-w-[560px] text-foreground/80'>
          Continue aprendendo para desbloquear suas primeiras conquistas.
        </p>
      </section>
    )
  }

  return (
    <div className='space-y-10'>
      {profileSummary ? (
        <ProfileSummaryCard
          level={profileSummary.level}
          totalXp={profileSummary.totalXp}
          xpForNextLevel={profileSummary.xpForNextLevel}
        />
      ) : null}
      {familyGroups.map((group) => (
        <AchievementFamilySection
          achievements={group.achievements}
          family={group.family}
          key={group.family}
        />
      ))}
      {historicalAchievements.length > 0 ? (
        <HistoricalAchievementsSection achievements={historicalAchievements} />
      ) : null}
    </div>
  )
}
