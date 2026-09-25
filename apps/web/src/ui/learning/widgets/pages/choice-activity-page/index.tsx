import { Button } from '@/ui/shadcn/button'

import { ChoiceQuestion } from './choice-question'
import {
  type ChoiceActivityPageProps,
  useChoiceActivityPage,
} from './use-choice-activity-page'

export type { ChoiceActivityPageProps } from './use-choice-activity-page'

const DIFFICULTY_LABELS = {
  easy: 'Fácil',
  medium: 'Média',
  hard: 'Difícil',
} as const

export const ChoiceActivityPage = (props: ChoiceActivityPageProps) => {
  const {
    activity,
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
  } = useChoiceActivityPage(props)

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

  return (
    <main className='mx-auto w-full max-w-7xl space-y-6 pb-8'>
      <header>
        {activity.isDiagnostic ? (
          <p className='rounded-md border border-border bg-muted px-4 py-3 text-sm text-foreground'>
            Diagnóstico em andamento. O resultado aparecerá apenas no resumo consolidado
            da Habilidade. Material de apoio e dicas não estão disponíveis nesta
            Atividade.
          </p>
        ) : null}
        <h1 className='text-sm font-medium text-muted-foreground'>{activity.title}</h1>
      </header>

      <ChoiceQuestion
        disabled={!activity.canSubmit || isSubmitting || isSubmissionLocked}
        difficultyLabel={DIFFICULTY_LABELS[activity.difficulty]}
        key={currentQuestion.key}
        onToggleOption={handleToggleOption}
        question={currentQuestion}
        questionNumber={currentQuestionNumber}
        selectedOptionKeys={selectedOptionKeys}
        totalQuestions={totalQuestions}
      />

      <div aria-live='polite' className='space-y-3 pt-1'>
        <p className='text-sm text-muted-foreground'>
          Suas respostas não ficam salvas se você sair antes de enviar.
        </p>
        {hasSubmissionError ? (
          <p
            className='rounded-md border border-selo-text bg-accent p-3 text-sm text-selo-text'
            role='alert'
          >
            Não foi possível enviar suas respostas. Tente novamente.
          </p>
        ) : null}
        <Button
          className='w-full bg-primary text-primary-foreground hover:bg-primary/90 sm:w-auto sm:min-w-44'
          disabled={!canContinue}
          onClick={handleContinue}
          type='button'
        >
          {isSubmitting
            ? 'Enviando respostas…'
            : hasSubmissionError
              ? 'Tentar enviar novamente'
              : isLastQuestion
                ? 'Enviar respostas'
                : 'Próxima questão'}
        </Button>
      </div>
    </main>
  )
}
