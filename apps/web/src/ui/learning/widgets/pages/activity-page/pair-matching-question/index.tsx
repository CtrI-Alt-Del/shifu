import { QuestionPrompt } from '@/ui/learning/widgets/components/question-prompt'
import { Button } from '@/ui/shadcn/button'
import { Icon } from '@/ui/shared/widgets/components/icon'

import { ActivityQuestionHeader } from '../components/activity-question-header'
import {
  type PairMatchingQuestionProps,
  usePairMatchingQuestion,
} from './use-pair-matching-question'

import './pair-matching-question.css'

export type { PairMatchingQuestionProps } from './use-pair-matching-question'

export const PairMatchingQuestion = (props: PairMatchingQuestionProps) => {
  const {
    selectedWordKey,
    announcement,
    isComplete,
    orderedPairs,
    sourceLanguageLabel,
    targetLanguageLabel,
    wordText,
    translationText,
    translationKeyByWord,
    wordKeyByTranslation,
    pairNumber,
    registerWordButton,
    handleSelectWord,
    handleSelectTranslation,
    handleRemovePair,
    handleKeyDown,
  } = usePairMatchingQuestion(props)
  const {
    activityTitle,
    difficulty,
    disabled = false,
    isDiagnostic,
    pairs,
    question,
    questionNumber,
    totalQuestions,
  } = props
  const questionLabelId = `pair-matching-question-${question.key}`

  return (
    <section
      aria-labelledby={questionLabelId}
      className='space-y-6'
      onKeyDown={handleKeyDown}
    >
      <ActivityQuestionHeader
        activityTitle={activityTitle}
        difficulty={difficulty}
        questionContext='associe palavras e traduções'
        questionNumber={questionNumber}
        showQuestionProgress={!isDiagnostic}
        totalQuestions={totalQuestions}
      />

      <div className='space-y-4'>
        <QuestionPrompt id={questionLabelId} prompt={question.prompt} />
        <dl className='grid grid-cols-1 gap-3 text-sm sm:grid-cols-2'>
          <div>
            <dt className='font-medium text-muted-foreground'>Idioma das palavras</dt>
            <dd className='text-foreground'>{sourceLanguageLabel}</dd>
          </div>
          <div>
            <dt className='font-medium text-muted-foreground'>Idioma das traduções</dt>
            <dd className='text-foreground'>{targetLanguageLabel}</dd>
          </div>
        </dl>
        <p className='text-sm text-muted-foreground'>
          Selecione uma palavra e depois a sua tradução. Selecione uma palavra já
          associada para trocar o par.
        </p>
      </div>

      <div className='grid grid-cols-1 gap-6 sm:grid-cols-2'>
        <div>
          <h2 className='mb-2 text-sm font-semibold text-foreground'>Palavras</h2>
          <ul className='space-y-2'>
            {question.words.map((word) => {
              const translationKey = translationKeyByWord.get(word.key)
              const isSelected = selectedWordKey === word.key
              const isPaired = translationKey !== undefined
              return (
                <li key={word.key}>
                  <Button
                    aria-label={
                      isPaired
                        ? `${word.text}, par ${pairNumber(word.key)} com ${translationText(translationKey)}`
                        : word.text
                    }
                    aria-pressed={isSelected}
                    className='pair-matching-item w-full justify-between gap-3 text-left'
                    data-paired={isPaired}
                    data-selected={isSelected}
                    disabled={disabled}
                    onClick={() => handleSelectWord(word.key)}
                    ref={registerWordButton(word.key)}
                    type='button'
                    variant='outline'
                  >
                    <span>{word.text}</span>
                    {isPaired ? (
                      <span aria-hidden='true' className='pair-matching-badge'>
                        <Icon className='size-4' name='check' />
                        Par {pairNumber(word.key)}
                      </span>
                    ) : isSelected ? (
                      <span aria-hidden='true' className='pair-matching-badge'>
                        <Icon className='size-4' name='circle-dashed' />
                        Selecionada
                      </span>
                    ) : null}
                  </Button>
                </li>
              )
            })}
          </ul>
        </div>
        <div>
          <h2 className='mb-2 text-sm font-semibold text-foreground'>Traduções</h2>
          <ul className='space-y-2'>
            {question.translations.map((translation) => {
              const wordKey = wordKeyByTranslation.get(translation.key)
              const isPaired = wordKey !== undefined
              return (
                <li key={translation.key}>
                  <Button
                    aria-label={
                      isPaired
                        ? `${translation.text}, par ${pairNumber(wordKey)} com ${wordText(wordKey)}`
                        : translation.text
                    }
                    className='pair-matching-item w-full justify-between gap-3 text-left'
                    data-paired={isPaired}
                    disabled={disabled}
                    onClick={() => handleSelectTranslation(translation.key)}
                    type='button'
                    variant='outline'
                  >
                    <span>{translation.text}</span>
                    {isPaired ? (
                      <span aria-hidden='true' className='pair-matching-badge'>
                        <Icon className='size-4' name='check' />
                        Par {pairNumber(wordKey)}
                      </span>
                    ) : null}
                  </Button>
                </li>
              )
            })}
          </ul>
        </div>
      </div>

      <div className='space-y-2'>
        <h2 className='text-sm font-semibold text-foreground'>Pares formados</h2>
        <p className='text-sm text-muted-foreground'>
          {pairs.length} de {question.words.length} pares formados.
          {isComplete && !disabled ? ' Você já pode avaliar a resposta.' : ''}
          {disabled && isComplete ? ' Resposta avaliada: não é possível alterar.' : ''}
        </p>
        {orderedPairs.length > 0 ? (
          <ul aria-label='Pares formados' className='space-y-2'>
            {orderedPairs.map((pair) => (
              <li
                className='flex items-center justify-between gap-3 rounded-md border border-border bg-muted px-3 py-2 text-sm'
                key={pair.wordKey}
              >
                <span>
                  <span className='font-medium'>Par {pairNumber(pair.wordKey)}:</span>{' '}
                  {wordText(pair.wordKey)} — {translationText(pair.translationKey)}
                </span>
                {disabled ? (
                  <span className='inline-flex items-center gap-1 text-xs text-muted-foreground'>
                    <Icon className='size-4' name='lock' />
                    Somente leitura
                  </span>
                ) : (
                  <Button
                    aria-label={`Remover par ${pairNumber(pair.wordKey)}: ${wordText(pair.wordKey)} e ${translationText(pair.translationKey)}`}
                    onClick={() => handleRemovePair(pair.wordKey)}
                    type='button'
                    variant='ghost'
                  >
                    <Icon className='size-4' name='x' />
                    Remover
                  </Button>
                )}
              </li>
            ))}
          </ul>
        ) : null}
      </div>

      <output aria-live='polite' className='sr-only'>
        {announcement}
      </output>
    </section>
  )
}
