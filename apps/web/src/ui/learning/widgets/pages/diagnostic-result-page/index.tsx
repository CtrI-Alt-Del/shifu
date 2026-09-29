import { Link } from '@tanstack/react-router'

import { Button } from '@/ui/shadcn/button'
import { SkillCompetencyList } from '@/ui/learning/widgets/pages/skill-page/skill-competency-list'
import { SkillRecommendationCard } from '@/ui/learning/widgets/pages/skill-page/skill-recommendation'

import {
  type DiagnosticResultPageProps,
  useDiagnosticResultPage,
} from './use-diagnostic-result-page'

export type { DiagnosticResultPageProps } from './use-diagnostic-result-page'

export const DiagnosticResultPage = (props: DiagnosticResultPageProps) => {
  const {
    diagnostic,
    experience,
    isLoading,
    isPrivateAbsence,
    isRecoverableError,
    handleRetry,
  } = useDiagnosticResultPage(props)

  if (isLoading) {
    return (
      <main className='mx-auto w-full max-w-7xl p-6'>
        <output
          aria-label='Carregando resultado...'
          className='block rounded-md bg-card p-5'
        >
          Carregando resultado...
        </output>
      </main>
    )
  }

  if (isPrivateAbsence) {
    return (
      <main className='mx-auto w-full max-w-7xl p-6 text-center'>
        <h1 className='font-serif text-3xl'>Resultado não encontrado</h1>
        <p className='mt-3 text-muted-foreground'>Este resultado não está disponível.</p>
      </main>
    )
  }

  if (isRecoverableError || !diagnostic || !experience) {
    return (
      <main
        className='mx-auto flex min-h-64 w-full max-w-7xl flex-col items-center justify-center gap-4 p-6 text-center'
        role='alert'
      >
        <h1 className='font-serif text-3xl'>Não foi possível carregar o resultado</h1>
        <Button onClick={() => void handleRetry()} type='button'>
          Tentar novamente
        </Button>
      </main>
    )
  }

  const isDirectCompletion = diagnostic.directCompletion
  const overallResult = diagnostic.initialOverallResult
  const competencies = diagnostic.competencies.map((competency) => ({
    competencyId: competency.competencyId,
    competencyName: competency.competencyName,
    position: competency.position,
    progress: competency.progress,
    coverageComplete: competency.coverageComplete,
    status: competency.status,
    availability: competency.contentReleased
      ? ('available' as const)
      : ('unavailable' as const),
    isFocus: competency.isFocus,
  }))
  const focusCompetencyName =
    competencies.find(({ competencyId }) => competencyId === diagnostic.focusCompetencyId)
      ?.competencyName ?? null
  const recommendation = diagnostic.initialRecommendation
  const hasBlockedCompetencies = competencies.some(
    ({ availability }) => availability === 'unavailable',
  )

  return (
    <main className='w-full mx-auto max-w-7xl space-y-8 px-5 py-8 pb-24 sm:pb-8'>
      <header className='mx-auto w-full space-y-3'>
        <h1 className='font-serif text-4xl font-semibold'>Seu ponto de partida</h1>
        <p className='max-w-2xl text-muted-foreground'>
          {isDirectCompletion
            ? 'Todas as Competências já estavam dominadas. Este diagnóstico concluiu a Habilidade sem indicar evolução.'
            : 'Este resumo consolidado mostra a base observada para cada Competência. Respostas e correções individuais não são exibidas.'}
        </p>
      </header>

      <section
        aria-labelledby='diagnostic-result-summary'
        className='mx-auto w-full rounded-md border border-border bg-card p-5 sm:p-6'
      >
        <h2 className='font-serif text-2xl font-semibold' id='diagnostic-result-summary'>
          Resultado geral
        </h2>
        <p className='mt-3 text-2xl font-semibold tabular-nums'>
          {overallResult === null ? 'Sem evidência' : `${Math.round(overallResult)}%`}
        </p>
        <p className='mt-2 text-sm text-muted-foreground'>
          Progresso demonstrado em todos os Conceitos da Habilidade. O status de cada
          Competência considera os Conceitos avaliados.
        </p>
      </section>

      <section
        aria-labelledby='diagnostic-result-competencies'
        className='mx-auto w-full space-y-4'
      >
        <h2
          className='text-sm font-medium text-secondary-foreground'
          id='diagnostic-result-competencies'
        >
          Ponto de partida por Competência (0–100)
        </h2>
        {hasBlockedCompetencies ? (
          <p className='text-sm text-muted-foreground'>
            O status de aprendizagem indica a evidência observada. “Bloqueada” indica que
            o conteúdo desta Competência ainda não foi liberado.
            {recommendation ? ' A recomendação abaixo é uma Atividade disponível.' : ''}
          </p>
        ) : null}
        <div className='rounded-md border border-control-border bg-card p-1.5 sm:p-2'>
          <SkillCompetencyList
            competencies={competencies}
            focusCompetencyName={focusCompetencyName}
            goalId={props.goalId}
            skillId={props.skillId}
          />
        </div>
      </section>

      {recommendation ? (
        <section className='mx-auto w-full space-y-3'>
          <h2 className='font-serif text-2xl font-semibold'>Próximo passo recomendado</h2>
          <p className='text-sm text-muted-foreground'>
            {recommendation.reason}
            {recommendation.targetConceptName
              ? ` Conceito em foco: ${recommendation.targetConceptName}.`
              : ''}
          </p>
          {recommendation.gap ? (
            <p className='text-sm text-muted-foreground'>{recommendation.gap}</p>
          ) : null}
          <SkillRecommendationCard
            goalId={props.goalId}
            recommendation={recommendation}
            skillId={props.skillId}
            viewSkillAction
          />
        </section>
      ) : diagnostic.initialRecommendationGap ? (
        <section
          aria-labelledby='diagnostic-result-recommendation-gap'
          className='mx-auto w-full space-y-3'
        >
          <h2
            className='font-serif text-2xl font-semibold'
            id='diagnostic-result-recommendation-gap'
          >
            Próximo passo indisponível
          </h2>
          <p className='text-sm text-muted-foreground'>
            Não foi possível recomendar uma atividade de aprendizagem com o conteúdo
            disponível neste momento.
          </p>
        </section>
      ) : null}

      {!recommendation ? (
        <div className='w-full'>
          <Link
            className='inline-flex min-h-11 items-center rounded-md border border-control-border px-4 font-semibold text-foreground hover:bg-muted'
            params={props}
            to='/learning/goals/$goalId/skills/$skillId'
          >
            Ver Habilidade
          </Link>
        </div>
      ) : null}
    </main>
  )
}
