import { motion } from 'motion/react'

import { ENTRANCE_ROW } from '@/constants/motion-variants'
import type { FillBlanksResultQuestion } from '@/core/learning/choice-activity'
import { QuestionPrompt } from '@/ui/learning/widgets/components/question-prompt'
import { Icon } from '@/ui/shared/widgets/components/icon'

import { useFillBlanksResult } from './use-fill-blanks-result'

export type FillBlanksResultProps = {
  questionNumber: number
  result: FillBlanksResultQuestion
}

export const FillBlanksResult = (props: FillBlanksResultProps) => {
  const { questionNumber, result } = props
  const {
    expectedItems,
    filledSegments,
    formattedScore,
    hasExpectedBlanks,
    isCorrect,
    outcome,
  } = useFillBlanksResult(props)

  return (
    <motion.details
      aria-labelledby={`choice-result-question-${questionNumber}`}
      className='choice-result-card group rounded-md border border-border bg-muted'
      variants={ENTRANCE_ROW}
    >
      <summary
        className='flex min-h-11 cursor-pointer list-none flex-col items-stretch gap-1 px-3 py-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring sm:flex-row sm:items-center sm:justify-between sm:gap-3 sm:px-4 [&::-webkit-details-marker]:hidden'
        id={`choice-result-question-${questionNumber}`}
      >
        <span className='flex min-w-0 flex-wrap items-center gap-x-2'>
          <span
            className={`flex items-center gap-1 text-sm font-semibold ${isCorrect ? 'text-success' : 'text-selo-text'}`}
          >
            {outcome ? (
              <Icon aria-hidden='true' name={outcome.iconName} size={16} />
            ) : null}
            Questão {questionNumber} · lacunas · {outcome?.label}
          </span>
          <span aria-hidden='true' className='text-muted-foreground'>
            ·
          </span>
          <span className='min-w-0 truncate text-sm text-muted-foreground'>
            {result.prompt}
          </span>
        </span>
        <span className='flex shrink-0 items-center justify-end gap-3'>
          <output
            aria-label={`Nota ${formattedScore} de 100`}
            className={`font-mono text-xs font-semibold ${isCorrect ? 'text-success' : 'text-selo-text'}`}
          >
            {formattedScore}
            <span className='ml-1 text-xs font-normal text-muted-foreground'>/ 100</span>
          </output>
          <Icon
            className='shrink-0 text-muted-foreground transition-transform duration-300 ease-out group-open:rotate-90'
            name='chevron-right'
            size={16}
          />
        </span>
      </summary>
      <div className='space-y-3 border-t border-border p-3 sm:p-4'>
        <QuestionPrompt
          id={`choice-result-question-${questionNumber}-prompt`}
          prompt={result.prompt}
          size='result'
        />
        <section
          aria-labelledby={`fill-blanks-result-fill-${questionNumber}`}
          className='space-y-2'
        >
          <div className='flex items-center justify-between gap-3'>
            <h3
              className='text-sm font-semibold'
              id={`fill-blanks-result-fill-${questionNumber}`}
            >
              Seu preenchimento
            </h3>
            <span className='text-xs text-muted-foreground'>Somente leitura</span>
          </div>
          <p className='whitespace-pre-wrap rounded-md border border-border bg-card p-3 text-sm leading-8'>
            {filledSegments.map((item, index) =>
              item.blankNumber === null ? (
                // biome-ignore lint/suspicious/noArrayIndexKey: the segment order is fixed by the Curriculum.
                <span key={`text-${index}`} lang={result.contentLanguage}>
                  {item.segment.text}
                </span>
              ) : (
                <span
                  className='mx-1 inline-block rounded-md border border-control-border bg-accent px-2 font-semibold'
                  key={item.segment.blankKey}
                >
                  <span className='sr-only'>Lacuna {item.blankNumber}: </span>
                  <span lang={result.contentLanguage}>{item.word ?? '—'}</span>
                </span>
              ),
            )}
          </p>
          {outcome ? (
            <p className='text-sm text-muted-foreground'>{outcome.countText}</p>
          ) : null}
        </section>
        {hasExpectedBlanks ? (
          <section
            aria-labelledby={`fill-blanks-result-expected-${questionNumber}`}
            className='space-y-2'
          >
            <h3
              className='text-sm font-semibold'
              id={`fill-blanks-result-expected-${questionNumber}`}
            >
              Preenchimento esperado
            </h3>
            <ul className='space-y-1 text-sm'>
              {expectedItems.map((item) => (
                <li key={item.blankKey}>
                  Lacuna {item.blankNumber}:{' '}
                  <span lang={result.contentLanguage}>{item.words.join(' ou ')}</span>
                </li>
              ))}
            </ul>
          </section>
        ) : null}
        <p className='whitespace-pre-wrap border-t border-border pt-2 text-sm leading-5 text-muted-foreground'>
          {result.explanation}
        </p>
      </div>
    </motion.details>
  )
}
