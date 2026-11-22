import { motion } from 'motion/react'

import { ENTRANCE_SECTION } from '@/constants/motion-variants'
import { Button } from '@/ui/shadcn/button'
import { Skeleton } from '@/ui/shadcn/skeleton'
import { Anchor } from '@/ui/shared/widgets/components/anchor'
import { Icon } from '@/ui/shared/widgets/components/icon'
import { MotionEntrance } from '@/ui/shared/widgets/components/motion-entrance'

import { CompletedSkillsCard } from './completed-skills-card'
import { RecentMasteriesCard } from './recent-masteries-card'
import { ResumeList } from './resume-list'
import { SkillEvolutionCard } from './skill-evolution-card'
import { StageDistributionCard } from './stage-distribution-card'
import { useLearningPanoramaSection } from './use-learning-panorama-section'
import { WeeklyEvaluationsCard } from './weekly-evaluations-card'

const CARD_CLASS_NAME = 'rounded-[14px] border border-border bg-surface-alt p-5'
const PAIR_GRID_CLASS_NAME = 'grid gap-4 lg:grid-cols-[minmax(0,848fr)_minmax(0,416fr)]'

export const LearningPanoramaSection = () => {
  const {
    state,
    panorama,
    isRetrying,
    weeklyData,
    hasWeeklyData,
    stageItems,
    stageSummary,
    handleRetry,
  } = useLearningPanoramaSection()

  return (
    <section
      aria-labelledby='learning-panorama-title'
      className='flex min-w-0 flex-col gap-4'
    >
      <h2
        className='flex items-center gap-2.5 pt-2 text-lg font-semibold text-foreground'
        id='learning-panorama-title'
      >
        <span aria-hidden='true' className='size-2.5 rounded-full bg-jade-fill' />
        Aprendizagem
      </h2>

      {state === 'loading' ? (
        <output
          aria-busy='true'
          aria-label='Carregando sua aprendizagem'
          className='block space-y-4'
        >
          <div aria-hidden='true' className={PAIR_GRID_CLASS_NAME}>
            <Skeleton className='h-56 rounded-[14px]' />
            <Skeleton className='h-56 rounded-[14px]' />
          </div>
          <div aria-hidden='true' className='grid gap-4 lg:grid-cols-2'>
            <Skeleton className='h-96 rounded-[14px]' />
            <Skeleton className='h-96 rounded-[14px]' />
          </div>
        </output>
      ) : null}

      {state === 'error' ? (
        <div className={`${CARD_CLASS_NAME} p-8 text-center`} role='alert'>
          <Icon className='mx-auto text-selo-text' name='circle-alert' size={32} />
          <h3 className='mt-4 font-serif text-2xl'>
            Não foi possível carregar sua aprendizagem
          </h3>
          <p className='mt-3 text-muted-foreground'>
            Seus dados continuam salvos. Tente novamente em alguns instantes.
          </p>
          <Button
            className='mt-6'
            disabled={isRetrying}
            onClick={handleRetry}
            type='button'
          >
            Tentar novamente
          </Button>
        </div>
      ) : null}

      {state === 'empty' ? (
        <MotionEntrance>
          <motion.div
            className={`${CARD_CLASS_NAME} flex flex-col items-center gap-3 p-8 text-center`}
            variants={ENTRANCE_SECTION}
          >
            <Icon className='text-jade-solid' name='target' size={32} />
            <h3 className='font-serif text-2xl'>
              Sua aprendizagem começa com um Objetivo
            </h3>
            <p className='max-w-xl text-muted-foreground'>
              Crie um Objetivo para acompanhar as suas Habilidades, Competências e
              avaliações neste painel.
            </p>
            <Anchor
              className='mt-2 inline-flex min-h-11 items-center justify-center rounded-md bg-primary px-4 font-semibold text-primary-foreground transition-colors hover:bg-primary/90'
              route='learningGoalsNew'
            >
              Criar objetivo
            </Anchor>
          </motion.div>
        </MotionEntrance>
      ) : null}

      {state === 'success' && panorama ? (
        <MotionEntrance className='flex flex-col gap-4'>
          <div className={PAIR_GRID_CLASS_NAME}>
            <ResumeList items={panorama.resumeItems} />
            <StageDistributionCard items={stageItems} summary={stageSummary} />
          </div>
          <div className='grid gap-4 lg:grid-cols-2'>
            <WeeklyEvaluationsCard data={weeklyData} hasData={hasWeeklyData} />
            <SkillEvolutionCard
              defaultSkillExperienceId={panorama.defaultEvolutionSkillExperienceId}
              options={panorama.evolutionOptions}
            />
          </div>
          <div className={PAIR_GRID_CLASS_NAME}>
            <CompletedSkillsCard skills={panorama.completedSkills} />
            <RecentMasteriesCard masteries={panorama.recentMasteries} />
          </div>
        </MotionEntrance>
      ) : null}
    </section>
  )
}
