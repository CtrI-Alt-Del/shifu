import type {
  ActivityQuestion,
  ActivityResultQuestion,
  CodeResultQuestion,
} from '@/core/learning/choice-activity'
import { Icon } from '@/ui/shared/widgets/components/icon'
import { QuestionPrompt } from '@/ui/learning/widgets/components/question-prompt'

import './choice-result-detail.css'

const SCORE_FORMATTER = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 })

export type ChoiceResultDetailProps = {
  question: ActivityQuestion | undefined
  result: ActivityResultQuestion
  questionNumber: number
}

export const ChoiceResultDetail = ({
  question,
  questionNumber,
  result,
}: ChoiceResultDetailProps) => {
  if (isCodeResultQuestion(result)) {
    const codeQuestion = question?.kind === 'javascript_stdin' ? question : undefined
    return (
      <details
        aria-labelledby={`choice-result-question-${questionNumber}`}
        className='choice-result-card group rounded-md border border-border bg-muted'
      >
        <summary
          className='flex min-h-11 cursor-pointer list-none flex-col items-stretch gap-1 px-3 py-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring sm:flex-row sm:items-center sm:justify-between sm:gap-3 sm:px-4 [&::-webkit-details-marker]:hidden'
          id={`choice-result-question-${questionNumber}`}
        >
          <span className='flex min-w-0 flex-wrap items-center gap-x-2'>
            <span className='text-sm font-semibold text-success'>
              Questão {questionNumber} · JavaScript · entrada padrão
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
              aria-label={`Nota ${formatNullableScore(result.score)} de 100`}
              className='font-mono text-xs font-semibold text-success'
            >
              {formatNullableScore(result.score)}
              <span className='ml-1 text-xs font-normal text-muted-foreground'>
                / 100
              </span>
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
          <section
            aria-labelledby={`code-result-files-${questionNumber}`}
            className='space-y-2'
          >
            <div className='flex items-center justify-between gap-3'>
              <h3
                className='text-sm font-semibold'
                id={`code-result-files-${questionNumber}`}
              >
                Arquivos enviados
              </h3>
              <span className='text-xs text-muted-foreground'>Somente leitura</span>
            </div>
            <div className='overflow-hidden rounded-md border border-border bg-card'>
              {result.submittedFiles.map((file) => (
                <article
                  className='border-b border-border last:border-b-0'
                  key={file.path}
                >
                  <h4 className='break-all border-b border-border px-3 py-2 font-mono text-xs text-muted-foreground'>
                    {file.path}
                  </h4>
                  <pre className='max-h-96 overflow-auto whitespace-pre-wrap p-3 font-mono text-xs text-foreground'>
                    {file.content}
                  </pre>
                </article>
              ))}
            </div>
          </section>
          {result.criterionResults.length > 0 ? (
            <section
              aria-labelledby={`code-result-rubric-${questionNumber}`}
              className='space-y-2'
            >
              <h3
                className='text-sm font-semibold'
                id={`code-result-rubric-${questionNumber}`}
              >
                Rubrica da questão
              </h3>
              <ul className='space-y-2'>
                {result.criterionResults.map((criterion) => (
                  <li
                    className='rounded-md border border-border bg-card p-3'
                    key={criterion.key}
                  >
                    <p className='text-sm font-semibold'>
                      {codeQuestion?.criteria.find(({ key }) => key === criterion.key)
                        ?.name ?? criterion.key}{' '}
                      · peso {criterion.weightPercentage}% · nível {criterion.level}
                    </p>
                    <p className='mt-1 text-sm text-muted-foreground'>
                      {criterion.comment}
                    </p>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
          {result.conceptObservations.length > 0 ? (
            <section
              aria-labelledby={`code-result-concepts-${questionNumber}`}
              className='space-y-2'
            >
              <h3
                className='text-sm font-semibold'
                id={`code-result-concepts-${questionNumber}`}
              >
                Evidências de Conceito
              </h3>
              <ul className='space-y-1 text-sm text-muted-foreground'>
                {result.conceptObservations.map((observation) => (
                  <li key={`${observation.conceptId}-${observation.observationId}`}>
                    {observation.conceptId} · nível {observation.level}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </div>
      </details>
    )
  }

  const formattedScore = SCORE_FORMATTER.format(Number(result.score))
  const choiceQuestion =
    question && question.kind !== 'javascript_stdin' ? question : undefined
  const visibleOptionKeys = new Set([
    ...result.submittedOptionKeys,
    ...(result.correctOptionKeys ?? []),
  ])
  const visibleOptions = (choiceQuestion?.options ?? []).filter((option) =>
    visibleOptionKeys.has(option.key),
  )

  return (
    <details
      aria-labelledby={`choice-result-question-${questionNumber}`}
      className='choice-result-card group rounded-md border border-border bg-muted'
    >
      <summary
        className='flex min-h-11 cursor-pointer list-none flex-col items-stretch gap-1 px-3 py-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring sm:flex-row sm:items-center sm:justify-between sm:gap-3 sm:px-4 [&::-webkit-details-marker]:hidden'
        id={`choice-result-question-${questionNumber}`}
      >
        <span className='flex min-w-0 flex-wrap items-center gap-x-2'>
          <span
            className={`text-sm font-semibold ${result.isCorrect ? 'text-success' : 'text-selo-text'}`}
          >
            Questão {questionNumber}
            {choiceQuestion
              ? ` · ${choiceQuestion.kind === 'multiple_selection' ? 'múltipla seleção' : 'escolha única'}`
              : ''}
            {' · '}
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
            className={`font-mono text-xs font-semibold ${result.isCorrect ? 'text-success' : 'text-selo-text'}`}
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
      <div className='space-y-2 border-t border-border p-3 sm:p-4'>
        <QuestionPrompt
          id={`choice-result-question-${questionNumber}-prompt`}
          prompt={result.prompt}
          size='result'
        />
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
                    <span className='shrink-0 text-xs font-semibold'>
                      Resposta correta
                    </span>
                  ) : null}
                </li>
              )
            })}
          </ul>
        ) : (
          <p className='text-sm text-muted-foreground'>
            Sua seleção não está disponível.
          </p>
        )}

        <p className='whitespace-pre-wrap border-t border-border pt-2 text-sm leading-5 text-muted-foreground'>
          {result.explanation}
        </p>
      </div>
    </details>
  )
}

function formatNullableScore(score: number | null) {
  return score === null ? '—' : SCORE_FORMATTER.format(Number(score))
}

function isCodeResultQuestion(
  result: ActivityResultQuestion,
): result is CodeResultQuestion {
  return 'kind' in result && result.kind === 'javascript_stdin'
}
