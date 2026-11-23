import type { ReactNode } from 'react'

import { PRACTICE_PHOTO_RULES_TEXT } from '@/core/learning/practice-photo-rules'
import { PracticalPreparationBrief } from '@/ui/learning/widgets/components/practical-preparation-brief'
import { QuestionPrompt } from '@/ui/learning/widgets/components/question-prompt'
import { Button } from '@/ui/shadcn/button'
import { Skeleton } from '@/ui/shadcn/skeleton'
import { Textarea } from '@/ui/shadcn/textarea'
import { Icon, type IconName } from '@/ui/shared/widgets/components/icon'

import { ActivityQuestionHeader } from '../components/activity-question-header'
import { PracticePhotoRecord } from './practice-photo-record'
import {
  type PracticalPreparationQuestionProps,
  type PracticeSaveState,
  usePracticalPreparationQuestion,
} from './use-practical-preparation-question'

export type {
  PracticalPreparationDraftState,
  PracticalPreparationQuestionProps,
} from './use-practical-preparation-question'

export type PracticalPreparationQuestionWidgetProps =
  PracticalPreparationQuestionProps & {
    isSubmitting?: boolean
    footer?: ReactNode
  }

const SAVE_STATE_ICONS: Record<PracticeSaveState, IconName> = {
  saved: 'circle-check',
  saving: 'clock-3',
  failed: 'triangle-alert',
}

export const PracticalPreparationQuestion = (
  props: PracticalPreparationQuestionWidgetProps,
) => {
  const {
    viewState,
    loadErrorMessage,
    isOffline,
    notice,
    records,
    reflection,
    isReflectionOpen,
    saveState,
    saveStateLabel,
    saveStateDetail,
    saveStateHelper,
    isComplete,
    isControlsDisabled,
    handleReloadDraft,
    handleToggleReflection,
    handleChangeReflection,
    handleBlurReflection,
    handleRetrySaveReflection,
    handleSelectPhoto,
    handleRetryPhoto,
    handleRemovePhoto,
  } = usePracticalPreparationQuestion(props)
  const {
    activityTitle,
    difficulty,
    footer,
    isSubmitting = false,
    question,
    questionNumber,
    totalQuestions,
  } = props
  const questionLabelId = `practical-preparation-question-${question.key}`
  const reflectionFieldId = `${questionLabelId}-reflection`
  const isDraftReady = viewState === 'ready'

  return (
    <section aria-labelledby={questionLabelId} className='space-y-6'>
      <ActivityQuestionHeader
        activityTitle={activityTitle}
        difficulty={difficulty}
        questionContext='preparação prática'
        questionNumber={questionNumber}
        showQuestionProgress
        totalQuestions={totalQuestions}
      />

      <div className='space-y-3'>
        <QuestionPrompt id={questionLabelId} prompt={question.prompt} />
        <p className='text-sm text-foreground'>
          Registre as fotos pedidas e envie. Seus critérios estão disponíveis antes de
          começar.
        </p>
      </div>

      <div className='grid gap-8 pt-4 lg:grid-cols-[minmax(0,1.36fr)_minmax(0,1fr)] lg:items-start'>
        <PracticalPreparationBrief question={question} />

        <div className='space-y-5 rounded-xl border border-border bg-card p-6'>
          {isSubmitting && isDraftReady ? (
            <div className='space-y-5'>
              <h2 className='font-serif text-2xl text-foreground'>
                Enviando sua Atividade…
              </h2>
              <output className='flex items-center gap-2 text-sm text-muted-foreground'>
                <Icon className='shrink-0' name='clock-3' size={16} />
                Enviando fotos e resposta…
              </output>
              <p className='text-sm text-foreground'>Aguarde a confirmação do envio.</p>
              <section
                aria-labelledby={`${questionLabelId}-sending`}
                className='space-y-2'
              >
                <h3
                  className='text-sm font-medium text-foreground'
                  id={`${questionLabelId}-sending`}
                >
                  Fotos para envio
                </h3>
                <ul className='grid grid-cols-3 gap-3'>
                  {records.map(({ record, thumbnailUrl }) => (
                    <li key={record.key}>
                      {thumbnailUrl ? (
                        <img
                          alt={`Foto do registro: ${record.label}`}
                          className='aspect-[3/2] w-full rounded-md border border-border object-cover'
                          height={96}
                          src={thumbnailUrl}
                          width={144}
                        />
                      ) : null}
                    </li>
                  ))}
                </ul>
                <p className='text-xs text-muted-foreground'>Envio em andamento.</p>
              </section>
              {footer}
            </div>
          ) : (
            <>
              <h2 className='font-serif text-2xl text-foreground'>Sua preparação</h2>
              <p className='text-sm text-muted-foreground'>{PRACTICE_PHOTO_RULES_TEXT}</p>

              {viewState === 'unavailable' ? (
                <p
                  className='flex items-center gap-2 text-sm text-selo-text'
                  role='alert'
                >
                  <Icon name='circle-alert' size={16} />
                  Não foi possível abrir o rascunho desta preparação.
                </p>
              ) : null}

              {viewState === 'offline' ? (
                <output className='flex items-center gap-2 text-sm text-muted-foreground'>
                  <Icon className='shrink-0' name='circle-pause' size={16} />
                  Sem conexão confirmada. Conecte-se para carregar e editar seu rascunho.
                </output>
              ) : null}

              {viewState === 'loading' ? (
                <output
                  aria-busy='true'
                  aria-label='Carregando rascunho...'
                  className='block space-y-3'
                >
                  {question.records.map((record) => (
                    <Skeleton
                      aria-hidden='true'
                      className='h-24 w-full'
                      key={record.key}
                    />
                  ))}
                  <span className='sr-only'>Carregando rascunho...</span>
                </output>
              ) : null}

              {viewState === 'error' ? (
                <div
                  className='space-y-3 rounded-md border border-selo-text bg-muted p-4'
                  role='alert'
                >
                  <p className='flex items-center gap-2 text-sm text-selo-text'>
                    <Icon className='shrink-0' name='triangle-alert' size={16} />
                    {loadErrorMessage}
                  </p>
                  <Button
                    onClick={() => void handleReloadDraft()}
                    type='button'
                    variant='outline'
                  >
                    Tentar novamente
                  </Button>
                </div>
              ) : null}

              {isDraftReady ? (
                <>
                  <div aria-live='polite' className='space-y-1'>
                    <p
                      className={`flex items-center gap-2 text-sm ${saveState === 'failed' ? 'text-selo-text' : 'text-muted-foreground'}`}
                    >
                      <Icon
                        className='shrink-0'
                        name={SAVE_STATE_ICONS[saveState]}
                        size={16}
                      />
                      <span>{saveStateLabel}</span>
                    </p>
                    {saveStateHelper ? (
                      <p className='text-sm text-foreground'>{saveStateHelper}</p>
                    ) : null}
                  </div>

                  {isOffline ? (
                    <output className='flex items-start gap-2 text-sm text-muted-foreground'>
                      <Icon className='mt-0.5 shrink-0' name='circle-pause' size={16} />
                      {saveStateDetail}
                    </output>
                  ) : null}

                  {saveState === 'failed' ? (
                    <div
                      className='space-y-2 rounded-md border border-border bg-muted p-4'
                      role='alert'
                    >
                      <p className='flex items-center gap-2 text-sm font-medium text-selo-text'>
                        <Icon className='shrink-0' name='triangle-alert' size={16} />
                        Não foi possível salvar as alterações
                      </p>
                      <p className='text-sm text-foreground'>{saveStateDetail}</p>
                      <Button
                        className='w-full'
                        disabled={isControlsDisabled}
                        onClick={handleRetrySaveReflection}
                        type='button'
                        variant='outline'
                      >
                        Tentar salvar novamente
                      </Button>
                    </div>
                  ) : null}

                  {notice === 'conflict' ? (
                    <output className='flex items-start gap-2 rounded-md border border-control-border bg-muted p-3 text-sm text-foreground'>
                      <Icon className='mt-0.5 shrink-0' name='info' size={16} />
                      Seu rascunho foi alterado em outro dispositivo. Mostramos a versão
                      salva. Confira as fotos e a reflexão antes de enviar de novo.
                    </output>
                  ) : null}

                  <ul aria-label='Registros fotográficos' className='space-y-5'>
                    {records.map((view, index) => (
                      <PracticePhotoRecord
                        isDisabled={isControlsDisabled}
                        key={view.record.key}
                        onRemovePhoto={(recordKey) => void handleRemovePhoto(recordKey)}
                        onRetryPhoto={(recordKey) => void handleRetryPhoto(recordKey)}
                        onSelectPhoto={(recordKey, file) =>
                          void handleSelectPhoto(recordKey, file)
                        }
                        position={index + 1}
                        view={view}
                      />
                    ))}
                  </ul>

                  <section className='space-y-3 border-t border-border pt-5'>
                    <button
                      aria-controls={reflectionFieldId}
                      aria-expanded={isReflectionOpen}
                      className='flex min-h-11 w-full items-center justify-between gap-3 rounded-md text-left font-medium text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring'
                      onClick={handleToggleReflection}
                      type='button'
                    >
                      <span>Sua percepção · opcional</span>
                      <Icon
                        className={`shrink-0 text-muted-foreground transition-transform ${isReflectionOpen ? 'rotate-90' : ''}`}
                        name='chevron-right'
                        size={16}
                      />
                    </button>
                    <p className='text-sm text-muted-foreground'>
                      Conte como ficaram o sabor, o aroma e a textura. Sua reflexão não
                      altera a nota.
                    </p>
                    {isReflectionOpen ? (
                      <div className='space-y-2' id={reflectionFieldId}>
                        <label
                          className='block text-sm font-medium text-foreground'
                          htmlFor={`${reflectionFieldId}-field`}
                        >
                          Seu relato sobre a preparação (escrito por você)
                        </label>
                        <Textarea
                          disabled={isControlsDisabled}
                          id={`${reflectionFieldId}-field`}
                          onBlur={handleBlurReflection}
                          onChange={(event) => handleChangeReflection(event.target.value)}
                          rows={5}
                          value={reflection}
                        />
                      </div>
                    ) : null}
                  </section>

                  {footer}
                  <p className='text-xs text-muted-foreground'>
                    {isComplete
                      ? 'As fotos enviadas ficam registradas nesta tentativa.'
                      : `Adicione as ${records.length} fotos para enviar a Atividade.`}
                  </p>
                </>
              ) : null}
            </>
          )}
        </div>
      </div>
    </section>
  )
}
