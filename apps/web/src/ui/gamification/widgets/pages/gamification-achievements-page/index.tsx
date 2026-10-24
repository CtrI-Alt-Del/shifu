import { motion } from 'motion/react'

import { ENTRANCE_SECTION } from '@/constants/motion-variants'
import { MotionEntrance } from '@/ui/shared/widgets/components/motion-entrance'
import { Button } from '@/ui/shadcn/button'
import { AnimatedNumber } from '@/ui/shared/widgets/components/animated-number'
import { Icon } from '@/ui/shared/widgets/components/icon'

import { AchievementFamilySection } from './achievement-family-section'
import { HistoricalAchievementsSection } from './historical-achievements-section'
import { useGamificationAchievementsPage } from './use-gamification-achievements-page'

export const GamificationAchievementsPage = () => {
  const {
    familyGroups,
    historicalAchievements,
    achievementsProgress,
    state,
    isRetrying,
    handleRetry,
  } = useGamificationAchievementsPage()

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
    <MotionEntrance className='space-y-8'>
      <motion.header className='space-y-2' variants={ENTRANCE_SECTION}>
        <div className='flex flex-wrap items-center justify-between gap-3'>
          <h2 className='font-serif text-[32px] leading-tight'>Conquistas</h2>
          {achievementsProgress ? (
            <p className='flex items-center gap-2 rounded-[6px] bg-latao-tint px-3 py-2 text-sm font-medium text-latao-text'>
              <Icon className='text-latao-solid' name='award' size={18} />
              <AnimatedNumber
                delay={0.3}
                format={(value) =>
                  `${value} de ${achievementsProgress.catalogCount} obtidas`
                }
                value={achievementsProgress.obtainedCount}
              />
            </p>
          ) : null}
        </div>
        <p className='text-sm leading-normal text-secondary-foreground'>
          Marcos da sua prática. As conquistas obtidas permanecem com você.
        </p>
      </motion.header>
      {familyGroups.map((group) => (
        <AchievementFamilySection
          achievements={group.achievements}
          family={group.family}
          key={group.family}
          obtainedCount={group.obtainedCount}
        />
      ))}
      {historicalAchievements.length > 0 ? (
        <HistoricalAchievementsSection achievements={historicalAchievements} />
      ) : null}
    </MotionEntrance>
  )
}
