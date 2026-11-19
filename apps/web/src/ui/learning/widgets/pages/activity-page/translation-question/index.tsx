import { QuestionPrompt } from '@/ui/learning/widgets/components/question-prompt'
import { Button } from '@/ui/shadcn/button'
import { Textarea } from '@/ui/shadcn/textarea'

import { ActivityQuestionHeader } from '../components/activity-question-header'
import {
  type TranslationQuestionProps,
  useTranslationQuestion,
} from './use-translation-question'

export type { TranslationQuestionProps } from './use-translation-question'

const DICTATION_STATUS_LABELS: Record<string, string> = {
  idle: '',
  preparing: 'Preparando o microfone…',
  recording: 'Gravando ditado…',
  transcribing: 'Transcrevendo o ditado…',
  review: 'Ditado pronto para revisão.',
  error: '',
}

export const TranslationQuestion = (props: TranslationQuestionProps) => {
  const {
    status,
    error,
    elapsedSeconds,
    languageAvailability,
    pendingTranscript,
    handleChangeText,
    handleStartDictation,
    handleStopDictation,
    handleCancelDictation,
    handleConfirmReplace,
    handleDeclineReplace,
  } = useTranslationQuestion(props)
  const {
    activityTitle,
    difficulty,
    disabled = false,
    isDiagnostic,
    question,
    questionNumber,
    totalQuestions,
    value,
  } = props
  const questionLabelId = `translation-question-${question.key}`
  const answerFieldId = `${questionLabelId}-answer`
  const dictationStatusId = `${questionLabelId}-dictation-status`
  const isDictationUnavailable = languageAvailability === 'unavailable'
  const isDictationBusy =
    status === 'preparing' || status === 'recording' || status === 'transcribing'
  const statusMessage = status === 'error' ? error : DICTATION_STATUS_LABELS[status]

  return (
    <section aria-labelledby={questionLabelId} className='space-y-6'>
      <ActivityQuestionHeader
        activityTitle={activityTitle}
        difficulty={difficulty}
        questionContext='traduza o texto'
        questionNumber={questionNumber}
        showQuestionProgress={!isDiagnostic}
        totalQuestions={totalQuestions}
      />

      <div className='space-y-4'>
        <QuestionPrompt id={questionLabelId} prompt={question.prompt} />
        <dl className='grid grid-cols-1 gap-3 text-sm sm:grid-cols-2'>
          <div>
            <dt className='font-medium text-muted-foreground'>Idioma de origem</dt>
            <dd className='text-foreground'>{question.sourceLanguage}</dd>
          </div>
          <div>
            <dt className='font-medium text-muted-foreground'>Idioma de destino</dt>
            <dd className='text-foreground'>{question.targetLanguage}</dd>
          </div>
        </dl>
        <div className='rounded-md border border-border bg-muted p-4'>
          <h2 className='text-sm font-semibold text-foreground'>Texto original</h2>
          <p className='mt-2 whitespace-pre-wrap text-sm text-foreground'>
            {question.sourceText}
          </p>
        </div>
      </div>

      <div className='space-y-2'>
        <label
          className='block text-sm font-medium text-foreground'
          htmlFor={answerFieldId}
        >
          Sua tradução
        </label>
        <Textarea
          disabled={disabled}
          id={answerFieldId}
          onChange={(event) => handleChangeText(event.target.value)}
          rows={6}
          value={value}
        />
      </div>

      {isDictationUnavailable ? (
        <p className='text-sm text-muted-foreground'>
          Ditado indisponível neste navegador. Continue digitando.
        </p>
      ) : (
        <fieldset
          aria-label='Ditado da tradução'
          className='space-y-2 rounded-md border border-border bg-card p-3'
        >
          <div className='flex flex-wrap items-center gap-2'>
            <Button
              aria-describedby={dictationStatusId}
              disabled={disabled || isDictationBusy}
              onClick={() => void handleStartDictation()}
              type='button'
            >
              Iniciar ditado
            </Button>
            <Button
              disabled={disabled || status !== 'recording'}
              onClick={handleStopDictation}
              type='button'
              variant='ghost'
            >
              Parar ditado
            </Button>
            <Button
              disabled={disabled || !isDictationBusy}
              onClick={handleCancelDictation}
              type='button'
              variant='ghost'
            >
              Cancelar ditado
            </Button>
          </div>
          <output
            aria-live='polite'
            className='block text-sm text-muted-foreground'
            id={dictationStatusId}
          >
            {status === 'recording'
              ? `${statusMessage} (${elapsedSeconds}s)`
              : statusMessage}
          </output>
          {status === 'error' && error ? (
            <p className='text-sm text-destructive' role='alert'>
              {error}
            </p>
          ) : null}
        </fieldset>
      )}

      {pendingTranscript !== null ? (
        <div
          aria-label='Confirmar substituição por ditado'
          aria-live='assertive'
          className='space-y-3 rounded-md border border-selo-text/40 bg-accent/50 p-3'
          role='alertdialog'
        >
          <p className='text-sm font-medium text-foreground'>
            Substituir texto por ditado?
          </p>
          <p className='whitespace-pre-wrap rounded-md bg-muted p-2 text-sm text-muted-foreground'>
            {pendingTranscript}
          </p>
          <div className='flex gap-2'>
            <Button onClick={handleConfirmReplace} type='button'>
              Confirmar
            </Button>
            <Button onClick={handleDeclineReplace} type='button' variant='ghost'>
              Cancelar
            </Button>
          </div>
        </div>
      ) : null}
    </section>
  )
}
