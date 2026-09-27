import { Button } from '@/ui/shadcn/button'

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
    isLoading,
    isPrivateAbsence,
    isRecoverableError,
    isSubmissionLocked,
    isLastQuestion,
    isSubmitting,
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
          aria-label='Carregando Atividade...'
          className='block space-y-4 rounded-md border border-border bg-card p-6'
        >
          <p>Carregando Atividade...</p>
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

  const isCodeQuestion = currentQuestion.kind === 'javascript_stdin'

  return (
    <div
      className={
        isCodeQuestion
          ? 'flex min-h-0 w-full max-w-none flex-1 flex-col lg:-mt-2 lg:-mb-1 lg:min-h-[calc(100dvh-7.25rem)]'
          : 'mx-auto w-full max-w-7xl'
      }
    >
      {activity.isDiagnostic ? (
        <header>
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
          onAssess={handleAssessCode}
          runnerFactory={runnerFactory}
        />
      ) : (
        <ChoiceQuestion
          activityTitle={activity.title}
          disabled={
            !activity.canSubmit ||
            isSubmitting ||
            isSubmissionLocked ||
            Boolean(feedback) ||
            isAssessing
          }
          difficulty={activity.difficulty}
          key={currentQuestion.key}
          onToggleOption={handleToggleOption}
          question={currentQuestion}
          questionNumber={currentQuestionNumber}
          selectedOptionKeys={selectedOptionKeys}
          totalQuestions={totalQuestions}
        />
      )}
      {isMixedActivity && feedback ? (
        <QuestionFeedback
          feedback={feedback}
          frozenAnswer={frozenAnswer}
          question={currentQuestion}
        />
      ) : null}

      {!isCodeQuestion ||
      hasFeedbackError ||
      hasSubmissionError ||
      feedback ||
      frozenAnswer ? (
        <div aria-live='polite' className='space-y-3 pt-1'>
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
          {currentQuestion.kind !== 'javascript_stdin' || feedback || frozenAnswer ? (
            <Button
              className='w-full bg-primary text-primary-foreground hover:bg-primary/90 sm:w-auto sm:min-w-44 mt-6'
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
