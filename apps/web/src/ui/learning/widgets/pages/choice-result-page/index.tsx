import { Button } from '@/ui/shadcn/button'

import type {
  ChoiceQuestion,
  ChoiceResultQuestion,
} from '@/core/learning/choice-activity'
import type { CompetencyProgressStatus } from '@/core/learning/competency-detail'

import { ChoiceResultDetail } from './choice-result-detail'
import { type ChoiceResultPageProps, useChoiceResultPage } from './use-choice-result-page'

export type { ChoiceResultPageProps } from './use-choice-result-page'

const SCORE_FORMATTER = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 })

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
      <main className='mx-auto w-full max-w-3xl'>
        <output
          aria-label='Carregando resultado da Atividade...'
          className='block space-y-4 rounded-md border border-border bg-card p-6'
        >
          <div
            aria-hidden='true'
            className='motion-safe:animate-pulse h-7 w-2/3 rounded bg-muted'
          />
          <div
            aria-hidden='true'
            className='motion-safe:animate-pulse h-20 rounded bg-muted'
          />
          <p>Carregando resultado da Atividade...</p>
        </output>
      </main>
    )
  }

  if (pageProps.state === 'private-absence') {
    return (
      <main className='mx-auto flex min-h-64 w-full max-w-3xl flex-col items-center justify-center rounded-md border border-border bg-card p-6 text-center'>
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
        className='mx-auto flex min-h-64 w-full max-w-3xl flex-col items-center justify-center rounded-md border border-border bg-card p-6 text-center'
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

  if (attempt.status === 'pending') {
    return (
      <main className='mx-auto w-full max-w-3xl space-y-4'>
        {pageProps.onReturnToActivity ? (
          <Button onClick={pageProps.onReturnToActivity} type='button'>
            Voltar para Atividade
          </Button>
        ) : null}
        <h1 className='font-serif text-3xl text-foreground'>Avaliação em andamento</h1>
        <output
          aria-live='polite'
          className='block rounded-md border border-border bg-card p-5 text-foreground'
        >
          Estamos avaliando suas respostas. Você pode sair; o resultado ficará disponível
          aqui.
        </output>
      </main>
    )
  }

  if (attempt.status === 'failed') {
    return (
      <main className='mx-auto w-full max-w-3xl space-y-4'>
        {pageProps.onReturnToActivity ? (
          <Button onClick={pageProps.onReturnToActivity} type='button'>
            Voltar para Atividade
          </Button>
        ) : null}
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
      </main>
    )
  }

  const questionByKey = new Map<string, ChoiceQuestion>(
    activity.questions.map((question) => [question.key, question]),
  )
  const resultQuestions = attempt.questions ?? []
  const formattedScore = SCORE_FORMATTER.format(Number(attempt.score))

  return (
    <main className='mx-auto w-full max-w-3xl space-y-5 pb-8'>
      {pageProps.onReturnToActivity ? (
        <Button onClick={pageProps.onReturnToActivity} type='button'>
          Voltar para Atividade
        </Button>
      ) : null}
      <header className='space-y-3 border-b border-border pb-5'>
        <p className='text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground'>
          {activity.title}
        </p>
        <h1 className='font-serif text-3xl text-foreground sm:text-4xl'>
          Resultado da Atividade
        </h1>
        {attempt.score !== undefined && attempt.score !== null ? (
          <output
            aria-label={`Nota da Atividade ${formattedScore} de 100`}
            className='font-mono text-2xl font-semibold text-foreground'
          >
            {formattedScore}
            <span className='ml-2 text-sm font-normal text-muted-foreground'>/ 100</span>
          </output>
        ) : null}
      </header>

      {attempt.progressBefore !== undefined &&
      attempt.progressBefore !== null &&
      attempt.progressAfter !== undefined &&
      attempt.progressAfter !== null ? (
        <section
          aria-labelledby='choice-result-progress-title'
          className='space-y-3 rounded-md border border-border bg-card p-4 sm:p-5'
        >
          <div className='flex flex-wrap items-center justify-between gap-2'>
            <h2
              className='font-semibold text-foreground'
              id='choice-result-progress-title'
            >
              Progresso da Competência
            </h2>
            {attempt.statusAfter ? (
              <span className='rounded-sm bg-muted px-2 py-1 text-xs text-foreground'>
                {PROGRESS_STATUS_LABELS[attempt.statusAfter]}
              </span>
            ) : null}
          </div>
          <p className='font-mono text-sm text-foreground'>
            {new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 }).format(
              attempt.progressBefore,
            )}
            {' → '}
            {new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 }).format(
              attempt.progressAfter,
            )}
          </p>
          <div
            aria-label='Progresso da Competência após a avaliação'
            aria-valuemax={100}
            aria-valuemin={0}
            aria-valuenow={attempt.progressAfter}
            className='h-2 w-full bg-muted'
            role='progressbar'
          >
            <div
              className='h-full bg-success'
              style={{ width: `${attempt.progressAfter}%` }}
            />
          </div>
        </section>
      ) : null}

      <section aria-label='Detalhes por questão' className='space-y-3'>
        {resultQuestions.map((result: ChoiceResultQuestion, index) => (
          <ChoiceResultDetail
            key={result.key}
            question={questionByKey.get(result.key)}
            questionNumber={index + 1}
            result={result}
          />
        ))}
      </section>

      {recommendation ? (
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
    </main>
  )
}
