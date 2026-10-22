import { Button } from '@/ui/shadcn/button'
import { Icon } from '@/ui/shared/widgets/components/icon'

import { AchievementsSummaryCard } from './achievements-summary-card'
import { LevelProgressCard } from './level-progress-card'
import { StreakSummaryCard } from './streak-summary-card'
import { useOverviewTabPanel } from './use-overview-tab-panel'

const MEANING_NOTE =
  'XP e nível reconhecem sua prática e constância. Eles não representam seu conhecimento nem o domínio das suas Competências.'

export type OverviewTabPanelProps = {
  onViewAchievements: () => void
}

export const OverviewTabPanel = ({ onViewAchievements }: OverviewTabPanelProps) => {
  const { overview, state, isRetrying, handleRetry } = useOverviewTabPanel()

  if (state === 'loading') {
    return (
      <output
        aria-busy='true'
        aria-label='Carregando sua visão geral'
        className='block space-y-5 rounded-[14px] border border-border bg-card p-6'
      >
        <div aria-hidden='true' className='h-32 w-full animate-pulse rounded bg-muted' />
        <div aria-hidden='true' className='h-48 animate-pulse rounded bg-muted' />
        <span className='sr-only'>Carregando sua visão geral</span>
      </output>
    )
  }

  if (state === 'error') {
    return (
      <section
        aria-labelledby='gamification-overview-error-title'
        className='rounded-[14px] border border-border bg-card p-8 text-center'
        role='alert'
      >
        <Icon className='mx-auto text-selo-text' name='circle-alert' size={32} />
        <h3
          autoFocus
          className='mt-4 font-serif text-2xl'
          id='gamification-overview-error-title'
          tabIndex={-1}
        >
          Não foi possível carregar sua visão geral
        </h3>
        <p className='mt-3 text-muted-foreground'>
          Seu progresso continua salvo. Tente novamente em alguns instantes.
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
    )
  }

  if (state === 'empty' || !overview) {
    return (
      <div className='space-y-6'>
        <section
          aria-labelledby='gamification-overview-empty-title'
          className='rounded-[14px] border border-border bg-card p-8 text-center'
        >
          <Icon className='mx-auto text-muted-foreground' name='sparkles' size={32} />
          <h3 className='mt-4 font-serif text-2xl' id='gamification-overview-empty-title'>
            Sua jornada começa agora
          </h3>
          <p className='mt-3 text-muted-foreground'>
            Conclua um diagnóstico ou pratique uma Atividade para começar a acumular XP,
            formar sua sequência de dias e desbloquear conquistas. Tudo o que você
            conquistar aparece aqui.
          </p>
        </section>

        <p className='text-[13px] text-muted-foreground'>{MEANING_NOTE}</p>
      </div>
    )
  }

  return (
    <div className='space-y-6'>
      <LevelProgressCard
        currentLevelXp={overview.currentLevelXp}
        level={overview.level}
        levelPercentage={overview.levelPercentage}
        nextLevelXp={overview.nextLevelXp}
        totalXp={overview.totalXp}
        xpForNextLevel={overview.xpForNextLevel}
      />

      <div className='grid gap-6 lg:grid-cols-2'>
        <StreakSummaryCard streak={overview.streak} />
        <AchievementsSummaryCard
          achievements={overview.achievements}
          onViewAchievements={onViewAchievements}
        />
      </div>

      <p className='text-[13px] text-muted-foreground'>{MEANING_NOTE}</p>
    </div>
  )
}
