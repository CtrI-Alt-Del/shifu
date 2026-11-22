import { motion } from 'motion/react'

import { ENTRANCE_ROW } from '@/constants/motion-variants'
import type {
  PairMatchingQuestion,
  PairMatchingResultQuestion,
} from '@/core/learning/choice-activity'
import { QuestionPrompt } from '@/ui/learning/widgets/components/question-prompt'
import { Icon } from '@/ui/shared/widgets/components/icon'

import { usePairMatchingResult } from './use-pair-matching-result'

export type PairMatchingResultProps = {
  question: PairMatchingQuestion | undefined
  questionNumber: number
  result: PairMatchingResultQuestion
}

export const PairMatchingResult = (props: PairMatchingResultProps) => {
  const { questionNumber, result } = props
  const { expectedItems, formattedScore, isFull, outcome, submittedItems } =
    usePairMatchingResult(props)
  const toneClassName = isFull ? 'text-success' : 'text-selo-text'

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
            className={`flex items-center gap-1 text-sm font-semibold ${toneClassName}`}
          >
            {outcome ? (
              <Icon aria-hidden='true' name={outcome.iconName} size={16} />
            ) : null}
            Questão {questionNumber} · Associação · {outcome?.label}
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
            className={`font-mono text-xs font-semibold ${toneClassName}`}
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
      <div className='space-y-4 border-t border-border p-3 sm:p-4'>
        <QuestionPrompt
          id={`choice-result-question-${questionNumber}-prompt`}
          prompt={result.prompt}
          size='result'
        />
        {outcome ? (
          <p
            className={`flex flex-wrap items-center gap-2 text-sm font-medium ${toneClassName}`}
          >
            <Icon aria-hidden='true' name={outcome.iconName} size={16} />
            <span>{outcome.label}</span>
            <span className='font-normal text-muted-foreground'>{outcome.countText}</span>
          </p>
        ) : null}
        <p className='text-sm text-foreground'>{result.explanation}</p>
        <section
          aria-labelledby={`pair-result-submitted-${questionNumber}`}
          className='space-y-2'
        >
          <h3
            className='text-sm font-semibold'
            id={`pair-result-submitted-${questionNumber}`}
          >
            Pares enviados
          </h3>
          <ul aria-label='Pares enviados' className='space-y-1 text-sm'>
            {submittedItems.map((item) => (
              <li key={item.key}>
                {item.wordText} — {item.translationText}
              </li>
            ))}
          </ul>
        </section>
        {expectedItems.length > 0 ? (
          <section
            aria-labelledby={`pair-result-expected-${questionNumber}`}
            className='space-y-2'
          >
            <h3
              className='text-sm font-semibold'
              id={`pair-result-expected-${questionNumber}`}
            >
              Pares esperados
            </h3>
            <ul aria-label='Pares esperados' className='space-y-1 text-sm'>
              {expectedItems.map((item) => (
                <li key={item.key}>
                  {item.wordText} — {item.translationText}
                </li>
              ))}
            </ul>
          </section>
        ) : null}
      </div>
    </motion.details>
  )
}
