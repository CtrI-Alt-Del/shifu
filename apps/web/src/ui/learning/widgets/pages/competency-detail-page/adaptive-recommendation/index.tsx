import { Link } from '@tanstack/react-router'

import type { AvailableCompetencyDetail } from '@/core/learning/competency-detail'
import { Icon } from '@/ui/shared/widgets/components/icon'

const REASON_LABELS: Record<string, string> = {
  verification: 'Precisamos confirmar uma evidência inconclusiva.',
  coverage: 'Ainda faltam evidências para cobrir este Conceito.',
  practice: 'Uma nova prática pode fortalecer este Conceito.',
  hard_confirmation: 'Falta confirmar o aprendizado em uma Atividade difícil.',
  consolidation: 'Uma Atividade pode consolidar o domínio alcançado.',
  regression: 'O desempenho recente pede uma nova verificação.',
  prerequisite: 'Fortaleça primeiro um Conceito necessário para avançar.',
}

const DIFFICULTY_LABELS = {
  easy: 'Fácil',
  medium: 'Média',
  hard: 'Difícil',
} as const

export type AdaptiveRecommendationProps = {
  detail: AvailableCompetencyDetail
}

export const AdaptiveRecommendation = ({ detail }: AdaptiveRecommendationProps) => {
  const recommendation = detail.adaptive
  if (!recommendation) return null

  const targetLabel = recommendation.targetConceptName ?? 'Conceito em foco'
  const activity = detail.items.find(
    (item) => item.kind === 'activity' && item.id === recommendation.activityId,
  )
  return (
    <section
      aria-labelledby='adaptive-recommendation-title'
      className='rounded-md border border-control-border bg-card p-5 sm:p-6'
    >
      <p className='text-xs font-bold uppercase tracking-[0.12em] text-primary'>
        Próximo passo sugerido
      </p>
      <h2
        className='mt-2 font-serif text-2xl font-semibold text-foreground'
        id='adaptive-recommendation-title'
      >
        {targetLabel}
      </h2>
      <p className='mt-2 text-sm leading-6 text-muted-foreground'>
        {REASON_LABELS[recommendation.reason] ??
          'Há uma nova oportunidade de avançar nesta Competência.'}
      </p>
      {detail.coverageComplete === false ? (
        <p className='mt-3 text-sm text-foreground'>
          A cobertura de evidências desta Competência ainda está incompleta.
        </p>
      ) : null}
      {detail.verificationCause ? (
        <p className='mt-3 text-sm text-foreground'>
          Há uma verificação de aprendizagem pendente.
        </p>
      ) : null}
      {recommendation.gap ? (
        <p className='mt-4 rounded-md border border-border bg-muted px-4 py-3 text-sm text-foreground'>
          Não há uma Atividade adequada disponível agora para este Conceito. Você pode
          explorar os conteúdos liberados abaixo.
        </p>
      ) : null}
      <div className='mt-5 flex flex-col gap-3 sm:flex-row sm:flex-wrap'>
        {recommendation.materialId ? (
          <Link
            className='inline-flex min-h-11 items-center justify-center gap-2 rounded-md border border-control-border px-4 py-2 text-sm font-semibold text-foreground hover:bg-muted'
            params={{
              goalId: detail.goalId,
              skillId: detail.skillId,
              competencyId: recommendation.materialCompetencyId ?? detail.competencyId,
              materialId: recommendation.materialId,
            }}
            to='/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/materials/$materialId'
          >
            <Icon name='book-open' size={17} />
            {recommendation.materialIsOptional ? 'Ler Material opcional' : 'Ler Material'}
          </Link>
        ) : null}
        {recommendation.activityId ? (
          <Link
            className='inline-flex min-h-11 items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90'
            params={{
              goalId: detail.goalId,
              skillId: detail.skillId,
              competencyId: recommendation.recommendedCompetencyId ?? detail.competencyId,
              activityId: recommendation.activityId,
            }}
            to='/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId'
          >
            {activity?.title ?? 'Abrir Atividade recomendada'}
            {recommendation.difficulty
              ? ` · ${DIFFICULTY_LABELS[recommendation.difficulty]}`
              : null}
            <Icon name='arrow-right' size={17} />
          </Link>
        ) : null}
      </div>
      {recommendation.materialId && recommendation.activityId ? (
        <p className='mt-3 text-xs text-muted-foreground'>
          O Material é opcional. Você pode começar pela Atividade.
        </p>
      ) : null}
    </section>
  )
}
