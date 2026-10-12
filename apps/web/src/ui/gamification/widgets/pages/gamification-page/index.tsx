import { Button } from '@/ui/shadcn/button'
import { Icon } from '@/ui/shared/widgets/components/icon'
import { ModulePageHeader } from '@/ui/shared/widgets/components/module-page-header'

import { AchievementFamilySection } from './achievement-family-section'
import { HistoricalAchievementsSection } from './historical-achievements-section'
import { ProfileSummaryCard } from './profile-summary-card'
import { useGamificationPage } from './use-gamification-page'

export const GamificationPage = () => {
  const {
    familyGroups,
    historicalAchievements,
    profileSummary,
    state,
    isRetrying,
    handleRetry,
  } = useGamificationPage()

  return (
    <div className='mx-auto w-full max-w-7xl space-y-10'>
      <ModulePageHeader
        description='Reconheça o esforço que sustenta seu aprendizado, sem transformar a jornada em uma competição.'
        eyebrow='Módulo gamificação'
        title='Cada passo merece ser visto.'
      />

      {state === 'loading' ? (
        <output
          aria-busy='true'
          aria-label='Carregando conquistas'
          className='block space-y-5 rounded-lg border border-border bg-card p-6'
        >
          <div
            aria-hidden='true'
            className='h-32 w-full animate-pulse rounded bg-muted'
          />
          <div aria-hidden='true' className='h-64 animate-pulse rounded bg-muted' />
          <span className='sr-only'>Carregando conquistas</span>
        </output>
      ) : state === 'error' ? (
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
          <p className='mt-3 text-muted-foreground'>
            Tente novamente em alguns instantes.
          </p>
          <Button
            className='mt-6'
            disabled={isRetrying}
            onClick={handleRetry}
            type='button'
          >
            Tentar novamente
          </Button>
        </section>
      ) : state === 'empty' ? (
        <section className='flex min-h-[320px] flex-col items-center justify-center rounded-[10px] border border-border bg-surface-alt p-8 text-center'>
          <span className='flex size-12 items-center justify-center rounded-full bg-muted'>
            <Icon className='text-foreground/80' name='trophy' size={22} />
          </span>
          <h2 className='mt-4 text-xl font-semibold'>
            Nenhuma conquista disponível ainda
          </h2>
          <p className='mt-4 max-w-[560px] text-foreground/80'>
            Continue aprendendo para desbloquear suas primeiras conquistas.
          </p>
        </section>
      ) : (
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
      )}
    </div>
  )
}
