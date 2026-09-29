import { Button } from '@/ui/shadcn/button'
import { Skeleton } from '@/ui/shadcn/skeleton'
import { Link } from '@tanstack/react-router'

import './choice-result-page.css'

import type {
  ActivityQuestion,
  ActivityResultQuestion,
} from '@/core/learning/choice-activity'
import type { CompetencyProgressStatus } from '@/core/learning/competency-detail'
import { AdaptiveRecommendation } from '@/ui/learning/widgets/pages/competency-detail-page/adaptive-recommendation'
import { Icon } from '@/ui/shared/widgets/components/icon'

import { ChoiceResultDetail } from './choice-result-detail'
import { type ChoiceResultPageProps, useChoiceResultPage } from './use-choice-result-page'

export type { ChoiceResultPageProps } from './use-choice-result-page'

const SCORE_FORMATTER = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 })
const PROGRESS_FORMATTER = new Intl.NumberFormat('pt-BR', {
  maximumFractionDigits: 1,
})

const PROGRESS_STATUS_LABELS: Record<CompetencyProgressStatus, string> = {
  learning: 'Em aprendizado',
  developing: 'Em desenvolvimento',
  proficient: 'Proficiente',
  mastered: 'Dominada',
}

export const ChoiceResultPage = (props: ChoiceResultPageProps) => {
  const { canRetry, handleRetryEvaluation, hasRetryError, isRetrying, renderProps } =
    useChoiceResultPage(props)
  const pageProps = 'attemptId' in props ? renderProps : props

  if (pageProps.state === 'loading') {
    return (
      <main className='mx-auto w-full max-w-7xl space-y-3 pb-8'>
        <output
          aria-busy='true'
          aria-label='Carregando resultado da Atividade...'
          className='block space-y-3'
        >
          <div
            aria-hidden='true'
            className='flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between'
          >
            <div>
              <Skeleton className='h-9 w-72 max-w-full sm:h-10' />
              <Skeleton className='mt-2 h-4 w-44' />
            </div>
            <div className='flex items-end gap-1'>
              <Skeleton className='h-10 w-16' />
              <Skeleton className='mb-0.5 h-4 w-12' />
            </div>
          </div>

          <section
            aria-hidden='true'
            className='flex flex-col gap-3 rounded-md border border-border bg-card px-4 py-3 sm:flex-row sm:items-center sm:gap-4'
          >
            <div className='min-w-0 space-y-2 sm:w-60 sm:shrink-0'>
              <Skeleton className='h-3 w-40' />
              <div className='flex gap-2'>
                <Skeleton className='h-4 w-16' />
                <Skeleton className='h-4 w-16' />
              </div>
              <Skeleton className='h-3 w-32' />
            </div>
            <div className='min-w-0 flex-1'>
              <Skeleton className='h-1.5 w-full rounded-full' />
              <Skeleton className='mt-2 h-4 w-full' />
            </div>
          </section>

          <section aria-hidden='true' className='space-y-1'>
            {['first', 'second', 'third', 'fourth', 'fifth'].map((key) => (
              <div
                className='flex min-h-11 flex-col gap-2 rounded-md border border-border bg-card px-3 py-2 sm:flex-row sm:items-center sm:justify-between sm:gap-3 sm:px-4'
                key={key}
              >
                <div className='flex min-w-0 flex-1 flex-wrap items-center gap-x-2 gap-y-1'>
                  <Skeleton className='h-4 w-40' />
                  <Skeleton className='h-4 w-36 max-w-full' />
                </div>
                <div className='flex shrink-0 items-center justify-end gap-3'>
                  <Skeleton className='h-4 w-12' />
                  <Skeleton className='size-4' />
                </div>
              </div>
            ))}
          </section>

          <section
            aria-hidden='true'
            className='space-y-3 rounded-md border border-control-border bg-card p-5 sm:p-6'
          >
            <Skeleton className='h-3 w-40' />
            <Skeleton className='h-8 w-64 max-w-full' />
            <Skeleton className='h-4 w-3/4 max-w-2xl' />
            <Skeleton className='h-11 w-full sm:w-64' />
          </section>

          <Skeleton className='h-11 w-56 max-w-full' aria-hidden='true' />
          <span className='sr-only'>Carregando resultado da Atividade...</span>
        </output>
      </main>
    )
  }

  if (pageProps.state === 'private-absence') {
    return (
      <main className='mx-auto flex min-h-64 w-full max-w-7xl flex-col items-center justify-center rounded-md border border-border bg-card p-6 text-center'>
        <h1 className='font-serif text-3xl text-foreground'>Resultado não encontrado</h1>
        <p className='mt-3 text-muted-foreground'>
          Não foi possível encontrar este resultado.
        </p>
      </main>
    )
  }

  if (pageProps.state === 'error') {
    return (
      <main
        className='mx-auto flex min-h-64 w-full max-w-7xl flex-col items-center justify-center rounded-md border border-border bg-card p-6 text-center'
        role='alert'
      >
        <h1 className='font-serif text-3xl text-foreground'>
          Não foi possível carregar o resultado
        </h1>
        <p className='mt-3 text-muted-foreground'>
          Seu envio continua salvo. Tente carregar novamente.
        </p>
        <Button className='mt-5' onClick={pageProps.onRetryLoad} type='button'>
          Tentar novamente
        </Button>
      </main>
    )
  }

  if (pageProps.state !== 'result') return null

  const { activity, attempt, onOpenRecommendation, recommendation } = pageProps
  const backToCompetencyLink = pageProps.detailIds ? (
    <Link
      className='inline-flex min-h-11 w-fit items-center justify-center gap-2 rounded-md border border-control-border px-4 font-semibold text-foreground transition-colors hover:bg-muted focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring'
      params={{
        goalId: pageProps.detailIds.goalId,
        skillId: pageProps.detailIds.skillId,
        competencyId: pageProps.detailIds.competencyId,
      }}
      to='/learning/goals/$goalId/skills/$skillId/competencies/$competencyId'
    >
      <Icon name='arrow-left' size={16} />
      Voltar para a Competência
    </Link>
  ) : null

  if (attempt.status === 'pending') {
    return (
      <main className='mx-auto w-full max-w-7xl space-y-6 pb-8'>
        <h1 className='font-serif text-3xl font-normal text-foreground sm:text-4xl'>
          Avaliação em andamento
        </h1>
        <output
          aria-busy='true'
          aria-live='polite'
          className='block overflow-hidden rounded-lg border border-border bg-card text-foreground'
        >
          <div aria-hidden='true' className='choice-result-pending-progress'>
            <span />
          </div>
          <div className='space-y-2 p-5 sm:p-7'>
            <p className='text-lg font-semibold sm:text-xl'>
              Estamos avaliando suas respostas.
            </p>
            <p className='max-w-2xl leading-relaxed text-muted-foreground'>
              Você pode sair; o resultado ficará disponível aqui.
            </p>
          </div>
        </output>
        {backToCompetencyLink}
      </main>
    )
  }

  if (attempt.status === 'failed') {
    return (
      <main className='mx-auto w-full max-w-7xl space-y-4'>
        <h1 className='font-serif text-3xl text-foreground'>
          A avaliação não pôde ser concluída
        </h1>
        <section
          aria-labelledby='choice-result-failure-title'
          className='space-y-4 rounded-md border border-selo-text bg-card p-5'
          role='alert'
        >
          <h2 className='font-semibold text-foreground' id='choice-result-failure-title'>
            Suas respostas continuam salvas
          </h2>
          <p className='text-muted-foreground'>
            {attempt.failureMessage ?? 'Tente novamente para concluir a avaliação.'}
          </p>
          {canRetry ? (
            <Button
              className='bg-primary text-primary-foreground hover:bg-primary/90'
              disabled={isRetrying}
              onClick={() => void handleRetryEvaluation()}
              type='button'
            >
              {isRetrying ? 'Reiniciando avaliação…' : 'Tentar novamente'}
            </Button>
          ) : null}
          {hasRetryError ? (
            <output className='text-sm text-selo-text'>
              Não foi possível reiniciar agora. Tente novamente.
            </output>
          ) : null}
        </section>
        {backToCompetencyLink}
      </main>
    )
  }

  const questionByKey = new Map<string, ActivityQuestion>(
    activity.questions.map((question) => [question.key, question]),
  )
  const resultQuestions: readonly ActivityResultQuestion[] = attempt.questions ?? []
  const formattedScore = SCORE_FORMATTER.format(Number(attempt.score))
  const correctQuestionCount = resultQuestions.filter(
    (result) =>
      ('isCorrect' in result && result.isCorrect) ||
      ('kind' in result && result.score === 100),
  ).length

  return (
    <main className='mx-auto w-full max-w-7xl space-y-3 pb-8'>
      <header className='flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between'>
        <div>
          <h1 className='font-serif text-3xl font-normal text-foreground sm:text-4xl'>
            Resultado da Atividade
          </h1>
          <p className='mt-1 text-sm text-muted-foreground'>{activity.title}</p>
        </div>
        {attempt.score !== undefined && attempt.score !== null ? (
          <output
            aria-label={`Nota da Atividade ${formattedScore} de 100`}
            className='flex items-end gap-1 text-success'
          >
            <span className='font-mono text-4xl font-semibold leading-none'>
              {formattedScore}
            </span>
            <span className='pb-0.5 font-mono text-sm text-muted-foreground'>/ 100</span>
            <span className='sr-only'>
              {' '}
              {correctQuestionCount} de {resultQuestions.length}{' '}
              {resultQuestions.length === 1 ? 'questão correta' : 'questões corretas'}
            </span>
          </output>
        ) : null}
      </header>

      {attempt.progressBefore !== undefined &&
      attempt.progressBefore !== null &&
      attempt.progressAfter !== undefined &&
      attempt.progressAfter !== null ? (
        <section
          aria-labelledby='choice-result-progress-title'
          className='flex flex-col gap-3 rounded-md border border-border bg-card px-4 py-3 sm:flex-row sm:items-center sm:gap-4'
        >
          <div className='min-w-0 sm:w-60 sm:shrink-0'>
            <h2
              className='text-xs font-medium text-muted-foreground'
              id='choice-result-progress-title'
            >
              Progresso demonstrado da Habilidade
            </h2>
            <div className='mt-1 flex flex-wrap items-center gap-2'>
              <p className='text-sm font-medium text-foreground'>
                <span className='sr-only'>Antes: </span>
                {PROGRESS_FORMATTER.format(attempt.progressBefore)}%
                <span aria-hidden='true'> → </span>
                <span className='sr-only'>Agora: </span>
                {PROGRESS_FORMATTER.format(attempt.progressAfter)}%
              </p>
              {attempt.statusAfter ? (
                <span className='text-xs text-muted-foreground'>
                  {PROGRESS_STATUS_LABELS[attempt.statusAfter]}
                </span>
              ) : null}
            </div>
          </div>
          <div className='min-w-0 flex-1'>
            <div
              aria-label='Progresso demonstrado da Habilidade após a avaliação'
              aria-valuemax={100}
              aria-valuemin={0}
              aria-valuenow={attempt.progressAfter}
              aria-valuetext={`${PROGRESS_FORMATTER.format(attempt.progressAfter)}%`}
              className='h-1.5 w-full overflow-hidden rounded-full bg-muted'
              role='progressbar'
            >
              <div
                className='h-full rounded-full bg-success'
                style={{ width: `${attempt.progressAfter}%` }}
              />
            </div>
            <p className='mt-1.5 text-xs leading-relaxed text-muted-foreground'>
              O progresso considera suas respostas nesta Atividade e as evidências
              anteriores. Não é a nota acima.
            </p>
          </div>
        </section>
      ) : null}

      <section aria-label='Detalhes por questão' className='space-y-1'>
        {resultQuestions.map((result, index) => (
          <ChoiceResultDetail
            key={result.key}
            question={questionByKey.get(result.key)}
            questionNumber={index + 1}
            result={result}
          />
        ))}
      </section>

      {pageProps.adaptiveDetail?.adaptive ? (
        <AdaptiveRecommendation detail={pageProps.adaptiveDetail} />
      ) : null}

      {pageProps.adaptiveLoadError && pageProps.detailIds ? (
        <section className='rounded-md border border-border bg-card p-4'>
          <p className='text-sm text-muted-foreground'>
            Não foi possível carregar a próxima recomendação agora. Seu resultado está
            salvo.
          </p>
          <Link
            className='mt-3 inline-flex min-h-11 items-center font-semibold text-primary underline-offset-4 hover:underline'
            params={pageProps.detailIds}
            to='/learning/goals/$goalId/skills/$skillId/competencies/$competencyId'
          >
            Ver Competência e próxima recomendação
          </Link>
        </section>
      ) : null}

      {recommendation &&
      !pageProps.adaptiveDetail?.adaptive &&
      !pageProps.adaptiveLoadError ? (
        <section
          aria-label='Próxima Atividade recomendada'
          className='flex flex-wrap items-center justify-between gap-4 rounded-md border border-border bg-card p-4'
        >
          <div>
            <p className='font-semibold text-foreground'>
              {recommendation.type === 'reinforcement'
                ? 'Atividade de reforço recomendada'
                : 'Nova Atividade recomendada'}
            </p>
            <p className='text-sm text-muted-foreground'>
              Dificuldade:{' '}
              {
                { easy: 'Fácil', medium: 'Média', hard: 'Difícil' }[
                  recommendation.difficulty
                ]
              }
            </p>
          </div>
          {onOpenRecommendation ? (
            <Button onClick={() => onOpenRecommendation(recommendation)} type='button'>
              Próxima Atividade
            </Button>
          ) : null}
        </section>
      ) : null}

      {backToCompetencyLink}
    </main>
  )
}
