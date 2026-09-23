import type {
  ChoiceQuestion,
  ChoiceResultQuestion,
} from '@/core/learning/choice-activity'

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
      className='space-y-4 rounded-md border border-border bg-card p-4 sm:p-5'
    >
      <header className='flex items-start justify-between gap-4'>
        <div className='min-w-0 space-y-1'>
          <p className='text-xs font-semibold uppercase tracking-[0.1em] text-muted-foreground'>
            Questão {questionNumber} · {result.isCorrect ? 'Correta' : 'Incorreta'}
          </p>
          <h2
            className='whitespace-pre-wrap text-base font-semibold text-foreground'
            id={`choice-result-question-${questionNumber}`}
          >
            {result.prompt}
          </h2>
        </div>
        <output
          aria-label={`Nota ${formattedScore} de 100`}
          className='shrink-0 font-mono text-lg font-semibold text-foreground'
        >
          {formattedScore}
          <span className='ml-1 text-xs font-normal text-muted-foreground'>/ 100</span>
        </output>
      </header>

      {visibleOptions.length > 0 ? (
        <ul
          aria-label={`Alternativas visíveis da questão ${questionNumber}`}
          className='space-y-2'
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
                className={`flex min-h-11 items-center justify-between gap-3 rounded-md border px-3 py-2 ${stateClassName}`}
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

      <p className='whitespace-pre-wrap border-t border-border pt-3 text-sm leading-6 text-muted-foreground'>
        {result.explanation}
      </p>
    </article>
  )
}
