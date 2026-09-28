import { Button } from '@/ui/shadcn/button'
import { Skeleton } from '@/ui/shadcn/skeleton'
import { getDiagnosticRun } from '@/ui/learning/diagnostic-run-session'

import { ChoiceQuestion } from './choice-question'
import { CodeQuestion } from './code-question'
import { QuestionFeedback } from './question-feedback'
import { type ActivityPageProps, useActivityPage } from './use-activity-page'

export type { ActivityPageProps } from './use-activity-page'

export const ActivityPage = (props: ActivityPageProps) => {
  const {
    activity,
    isMixedActivity,
    canContinue,
    currentQuestion,
    currentQuestionNumber,
    handleContinue,
    handleToggleOption,
    hasSubmissionError,
    handleRetryLoad,
    handleReturnToSkill,
    isLoading,
    isPrivateAbsence,
    isInvalidated,
    isDiagnosticEntryRequired,
    isRecoverableError,
    isSubmissionLocked,
    isLastQuestion,
    isSubmitting,
    isDiagnosticProcessing,
    diagnosticStatus,
    hasDiagnosticStatusError,
    diagnosticRetryError,
    diagnosticCompletionError,
    isRetryingDiagnostic,
    isCompletingDiagnostic,
    handleRetryDiagnostic,
    handleRetryDiagnosticStatus,
    handleRetryDiagnosticCompletion,
    selectedOptionKeys,
    totalQuestions,
    feedback,
    frozenAnswer,
    isAssessing,
    hasFeedbackError,
    handleAssessCode,
    handleCodeFilesChange,
    runnerFactory,
  } = useActivityPage(props)

  if (isLoading) {
    return (
      <main className='mx-auto w-full max-w-7xl'>
        <output
          aria-busy='true'
          aria-label='Carregando Atividade...'
          className='block space-y-6'
        >
          <section aria-hidden='true' className='space-y-6'>
            <div className='shrink-0 space-y-2'>
              <div className='flex min-h-10 flex-wrap items-center justify-between gap-x-4 gap-y-2'>
                <div className='space-y-1'>
                  <Skeleton className='h-4 w-36' />
                  <Skeleton className='h-6 w-16' />
                </div>
                <Skeleton className='h-4 w-64 max-w-full' />
              </div>
              <Skeleton className='mx-4 h-1 w-[calc(100%-2rem)] rounded-none' />
            </div>

            <Skeleton className='h-8 w-4/5 max-w-xl sm:h-9' />

            <div className='space-y-2'>
              {['first', 'second'].map((key) => (
                <div
                  className='flex h-[50px] items-center gap-3 rounded-md border border-border bg-card px-4'
                  key={key}
                >
                  <Skeleton className='size-5 rounded-full' />
                  <Skeleton className='h-4 w-24' />
                </div>
              ))}
            </div>
          </section>
          <Skeleton className='h-11 w-full sm:w-44' />
          <span className='sr-only'>Carregando Atividade...</span>
        </output>
      </main>
    )
  }

  if (isPrivateAbsence) {
    return (
      <main className='mx-auto max-w-7xl p-6 text-center'>
        <h1 className='font-serif text-3xl'>Atividade não encontrada</h1>
      </main>
    )
  }

  if (isInvalidated) {
    return (
      <main className='mx-auto flex min-h-64 w-full max-w-7xl flex-col items-center justify-center gap-4 p-6 text-center'>
        <h1 className='font-serif text-3xl'>Este diagnóstico foi substituído</h1>
        <p role='alert'>
          Outra aba iniciou uma nova execução. As respostas desta aba não serão usadas.
        </p>
        <Button onClick={handleReturnToSkill} type='button'>
          Voltar à Habilidade
        </Button>
      </main>
    )
  }

  if (isDiagnosticEntryRequired) return null

  if (isDiagnosticProcessing && !activity) {
    return (
      <main className='mx-auto w-full max-w-7xl px-5 py-8 sm:px-10 lg:px-20'>
        <h1 className='font-serif text-4xl font-semibold'>Diagnóstico</h1>
        <output aria-live='polite' className='mt-6 block text-sm'>
          {diagnosticStatus === 'failed'
            ? 'A avaliação falhou no Shifu. Sua resposta foi preservada.'
            : diagnosticCompletionError
              ? 'Não foi possível consolidar o resultado.'
              : 'Avaliando o diagnóstico…'}
        </output>
        {diagnosticStatus === 'failed' ? (
          <Button
            disabled={isRetryingDiagnostic}
            onClick={() => void handleRetryDiagnostic()}
            type='button'
          >
            {isRetryingDiagnostic ? 'Tentando novamente…' : 'Tentar avaliação novamente'}
          </Button>
        ) : null}
        {diagnosticCompletionError ? (
          <Button onClick={() => void handleRetryDiagnosticCompletion()} type='button'>
            Tentar novamente
          </Button>
        ) : null}
        {hasDiagnosticStatusError ? (
          <Button onClick={() => void handleRetryDiagnosticStatus()} type='button'>
            Atualizar avaliação
          </Button>
        ) : null}
        {diagnosticRetryError ? (
          <p role='alert'>Não foi possível tentar novamente agora.</p>
        ) : null}
      </main>
    )
  }

  if (isRecoverableError || !activity) {
    return (
      <main
        className='mx-auto flex min-h-64 max-w-7xl flex-col items-center justify-center gap-4 text-center'
        role='alert'
      >
        <h1 className='font-serif text-3xl'>Não foi possível carregar esta Atividade</h1>
        <Button onClick={() => void handleRetryLoad()} type='button'>
          Tentar novamente
        </Button>
      </main>
    )
  }

  if (!currentQuestion) return null

  const diagnosticPosition =
    'goalId' in props
      ? (getDiagnosticRun(props.goalId, props.skillId)?.sequence ?? []).findIndex(
          (item) =>
            item.competencyId === props.competencyId &&
            item.activityId === props.activityId,
        )
      : -1
  const diagnosticSequence =
    'goalId' in props
      ? (getDiagnosticRun(props.goalId, props.skillId)?.sequence ?? [])
      : []
  const nextDiagnosticActivity = diagnosticSequence[diagnosticPosition + 1]
  const isLastDiagnosticActivity =
    diagnosticPosition >= 0 && diagnosticPosition === diagnosticSequence.length - 1
  const isNextCompetency =
    'goalId' in props && nextDiagnosticActivity?.competencyId !== props.competencyId

  const isCodeQuestion = currentQuestion.kind === 'javascript_stdin'
  const isDiagnosticChoice = activity.isDiagnostic && !isCodeQuestion
  const choiceQuestion =
    currentQuestion.kind !== 'javascript_stdin' ? (
      <ChoiceQuestion
        activityTitle={isDiagnosticChoice ? undefined : activity.title}
        difficulty={isDiagnosticChoice ? undefined : activity.difficulty}
        disabled={
          !activity.canSubmit ||
          isSubmitting ||
          isSubmissionLocked ||
          Boolean(feedback) ||
          isAssessing
        }
        key={currentQuestion.key}
        onToggleOption={handleToggleOption}
        question={currentQuestion}
        questionNumber={currentQuestionNumber}
        selectedOptionKeys={selectedOptionKeys}
        totalQuestions={totalQuestions}
      />
    ) : null

  return (
    <div
      className={
        isCodeQuestion
          ? 'flex min-h-0 w-full max-w-none flex-1 flex-col lg:-mt-2 lg:-mb-1 lg:min-h-[calc(100dvh-7.25rem)]'
          : isDiagnosticChoice
            ? 'mx-auto w-full max-w-7xl space-y-6 px-5 py-8 sm:px-10 lg:px-20'
            : 'mx-auto w-full max-w-7xl'
      }
    >
      {isDiagnosticChoice ? (
        <header className='max-w-4xl space-y-3'>
          <h1 className='font-serif text-4xl font-semibold'>Diagnóstico</h1>
          <h2 className='text-xl font-semibold'>{activity.title}</h2>
          <p className='max-w-2xl text-sm text-muted-foreground'>
            O resultado aparecerá apenas no resumo consolidado. Materiais de apoio e dicas
            não estão disponíveis nesta Atividade.
          </p>
        </header>
      ) : activity.isDiagnostic ? (
        <header className='mb-6'>
          <p className='rounded-md border border-border bg-muted px-4 py-3 text-sm text-foreground'>
            Diagnóstico em andamento. O resultado aparecerá apenas no resumo consolidado
            da Habilidade. Material de apoio e dicas não estão disponíveis nesta
            Atividade.
          </p>
        </header>
      ) : null}

      {isCodeQuestion ? (
        <CodeQuestion
          activityTitle={activity.title}
          difficulty={activity.difficulty}
          key={currentQuestion.key}
          question={currentQuestion}
          questionNumber={currentQuestionNumber}
          totalQuestions={totalQuestions}
          disabled={Boolean(feedback || frozenAnswer || isSubmissionLocked)}
          onFilesChange={handleCodeFilesChange}
          onAssess={activity.isDiagnostic ? undefined : handleAssessCode}
          runnerFactory={runnerFactory}
        />
      ) : isDiagnosticChoice ? (
        <section className='rounded-md border border-control-border bg-card p-5 sm:p-6'>
          {choiceQuestion}
        </section>
      ) : (
        choiceQuestion
      )}
      {isMixedActivity && !activity.isDiagnostic && feedback ? (
        <QuestionFeedback
          feedback={feedback}
          frozenAnswer={frozenAnswer}
          question={currentQuestion}
        />
      ) : null}

      {!isCodeQuestion ||
      activity.isDiagnostic ||
      hasFeedbackError ||
      hasSubmissionError ||
      feedback ||
      frozenAnswer ? (
        <div
          aria-live='polite'
          className={
            isDiagnosticChoice
              ? 'flex flex-col gap-3 pt-1 sm:items-end'
              : 'space-y-3 pt-1'
          }
        >
          {hasFeedbackError ? (
            <p role='alert'>Não foi possível avaliar. Tente novamente.</p>
          ) : null}
          {hasSubmissionError ? (
            <p
              className='rounded-md border border-selo-text bg-accent p-3 text-sm text-selo-text'
              role='alert'
            >
              Não foi possível enviar suas respostas. Tente novamente.
            </p>
          ) : null}
          {isDiagnosticProcessing ? (
            <div aria-live='polite' className='mt-6 space-y-3 text-sm'>
              <p>
                {diagnosticStatus === 'failed'
                  ? 'A avaliação falhou no Shifu. Sua resposta foi preservada.'
                  : diagnosticCompletionError
                    ? 'Não foi possível consolidar o resultado.'
                    : isCompletingDiagnostic
                      ? 'Consolidando o resultado…'
                      : 'Avaliando o diagnóstico…'}
              </p>
              {diagnosticStatus === 'failed' ? (
                <Button
                  disabled={isRetryingDiagnostic}
                  onClick={() => void handleRetryDiagnostic()}
                  type='button'
                >
                  {isRetryingDiagnostic
                    ? 'Tentando novamente…'
                    : 'Tentar avaliação novamente'}
                </Button>
              ) : null}
              {diagnosticCompletionError ? (
                <Button
                  onClick={() => void handleRetryDiagnosticCompletion()}
                  type='button'
                >
                  Tentar novamente
                </Button>
              ) : null}
              {hasDiagnosticStatusError ? (
                <Button onClick={() => void handleRetryDiagnosticStatus()} type='button'>
                  Atualizar avaliação
                </Button>
              ) : null}
              {diagnosticRetryError ? (
                <p role='alert'>Não foi possível tentar novamente agora.</p>
              ) : null}
            </div>
          ) : currentQuestion.kind !== 'javascript_stdin' ||
            activity.isDiagnostic ||
            feedback ||
            frozenAnswer ? (
            <Button
              className='mt-6 w-full bg-primary text-primary-foreground hover:bg-primary/90 sm:w-auto sm:min-w-44'
              disabled={!canContinue}
              onClick={handleContinue}
              type='button'
            >
              {isAssessing
                ? 'Avaliando questão…'
                : isSubmitting
                  ? 'Enviando respostas…'
                  : hasSubmissionError
                    ? 'Tentar enviar novamente'
                    : activity.isDiagnostic
                      ? isLastQuestion
                        ? isLastDiagnosticActivity
                          ? 'Enviar diagnóstico'
                          : isNextCompetency
                            ? 'Próxima competência'
                            : 'Próxima questão'
                        : 'Próxima questão'
                      : !isMixedActivity
                        ? isLastQuestion
                          ? 'Enviar respostas'
                          : 'Próxima questão'
                        : !feedback
                          ? frozenAnswer
                            ? 'Tentar avaliação novamente'
                            : 'Avaliar resposta'
                          : feedback.status === 'inconclusive'
                            ? 'Reavaliar resposta'
                            : isLastQuestion
                              ? 'Enviar respostas'
                              : 'Próxima questão'}
            </Button>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
