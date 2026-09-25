import type {
  ChoiceQuestion,
  ChoiceResultQuestion,
} from '@/core/learning/choice-activity'
import { QuestionPrompt } from '@/ui/learning/widgets/components/question-prompt'

import './choice-result-detail.css'

const SCORE_FORMATTER = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 })

export type ChoiceResultDetailProps = {
  question: ChoiceQuestion | undefined
  result: ChoiceResultQuestion
  questionNumber: number
}

export const ChoiceResultDetail = ({
  question,
  questionNumber,
  result,
}: ChoiceResultDetailProps) => {
  const formattedScore = SCORE_FORMATTER.format(Number(result.score))
  const visibleOptionKeys = new Set([
    ...result.submittedOptionKeys,
    ...(result.correctOptionKeys ?? []),
  ])
  const visibleOptions = (question?.options ?? []).filter((option) =>
    visibleOptionKeys.has(option.key),
  )

  return (
    <article
      aria-labelledby={`choice-result-question-${questionNumber}`}
      className='choice-result-card space-y-2 rounded-md border border-border bg-muted p-3 sm:p-4'
    >
      <header className='flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between sm:gap-4'>
        <div className='min-w-0 space-y-1'>
          <p
            className={`text-sm font-medium ${result.isCorrect ? 'text-success' : 'text-selo-text'}`}
          >
            Questão {questionNumber}
            {question
              ? ` · ${question.kind === 'multiple_selection' ? 'múltipla seleção' : 'escolha única'}`
              : ''}
            {' · '}
            {result.isCorrect ? 'correta' : 'incorreta'}
          </p>
          <QuestionPrompt
            id={`choice-result-question-${questionNumber}`}
            prompt={result.prompt}
            size='result'
          />
        </div>
        <output
          aria-label={`Nota ${formattedScore} de 100`}
          className='shrink-0 font-mono text-xs font-semibold text-foreground'
        >
          {formattedScore}
          <span className='ml-1 text-xs font-normal text-muted-foreground'>/ 100</span>
        </output>
      </header>

      {visibleOptions.length > 0 ? (
        <ul
          aria-label={`Alternativas visíveis da questão ${questionNumber}`}
          className='space-y-1'
        >
          {visibleOptions.map((option) => {
            const isSelected = result.submittedOptionKeys.includes(option.key)
            const isReleasedCorrect =
              result.correctOptionKeys?.includes(option.key) ?? false
            const stateClassName = isReleasedCorrect
              ? 'border-success bg-success/10 text-foreground'
              : isSelected
                ? 'border-selo-text bg-accent text-foreground'
                : 'border-control-border bg-muted text-foreground'

            return (
              <li
                className={`flex items-center justify-between gap-2 rounded-md border px-2 py-1.5 text-xs ${stateClassName}`}
                key={option.key}
              >
                <span className='whitespace-pre-wrap'>{option.text}</span>
                {isSelected ? (
                  <span className='shrink-0 text-xs font-semibold'>Sua resposta</span>
                ) : null}
                {!isSelected && isReleasedCorrect ? (
                  <span className='shrink-0 text-xs font-semibold'>Resposta correta</span>
                ) : null}
              </li>
            )
          })}
        </ul>
      ) : (
        <p className='text-sm text-muted-foreground'>Sua seleção não está disponível.</p>
      )}

      <p className='whitespace-pre-wrap border-t border-border pt-2 text-sm leading-5 text-muted-foreground'>
        {result.explanation}
      </p>
    </article>
  )
}
