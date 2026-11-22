import { motion } from 'motion/react'

import { ENTRANCE_ROW } from '@/constants/motion-variants'
import type { ImageChoiceResultQuestion } from '@/core/learning/choice-activity'
import { ImageChoiceOptions } from '@/ui/learning/widgets/components/image-choice-options'
import { QuestionPrompt } from '@/ui/learning/widgets/components/question-prompt'
import { Icon } from '@/ui/shared/widgets/components/icon'

const SCORE_FORMATTER = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 })

export type ImageChoiceResultProps = {
  questionNumber: number
  result: ImageChoiceResultQuestion
}

export const ImageChoiceResult = ({ questionNumber, result }: ImageChoiceResultProps) => {
  const promptId = `choice-result-question-${questionNumber}-prompt`
  const formattedScore = SCORE_FORMATTER.format(Number(result.score))
  const toneClassName = result.isCorrect ? 'text-success' : 'text-selo-text'

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
          <span className={`text-sm font-semibold ${toneClassName}`}>
            Questão {questionNumber} · escolha por imagem ·{' '}
            {result.isCorrect ? 'correta' : 'incorreta'}
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
        <QuestionPrompt id={promptId} prompt={result.prompt} size='result' />
        <ImageChoiceOptions
          disclosedCorrectOptionKey={result.disclosedCorrectOptionKey}
          isCorrect={result.isCorrect}
          labelledBy={promptId}
          name={`image-choice-result-${questionNumber}`}
          options={result.options}
          selectedOptionKey={result.selectedOptionKey}
          state='history'
        />
        <div
          className={`space-y-2 rounded-xl p-4 ${result.isCorrect ? 'bg-jade-tint' : 'bg-accent'}`}
        >
          <h3
            className={`flex items-center gap-2 text-base font-semibold ${result.isCorrect ? 'text-jade-text' : 'text-selo-text'}`}
          >
            <Icon aria-hidden='true' name={result.isCorrect ? 'check' : 'x'} size={20} />
            {result.isCorrect ? 'Resposta correta' : 'Resposta incorreta'}
          </h3>
          <p className='text-sm text-foreground'>{result.optionFeedback}</p>
          <p className='whitespace-pre-wrap text-sm text-secondary-foreground'>
            {result.explanation}
          </p>
        </div>
      </div>
    </motion.details>
  )
}
