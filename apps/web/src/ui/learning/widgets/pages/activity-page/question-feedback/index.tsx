import type { CSSProperties } from 'react'

import type {
  ActivityQuestion,
  ActivityAnswer,
  PreliminaryQuestionResult,
} from '@/core/learning/choice-activity'

import './question-feedback.css'
import { useQuestionFeedback } from './use-question-feedback'

export type QuestionFeedbackProps = {
  feedback: PreliminaryQuestionResult
  frozenAnswer: ActivityAnswer | null
  question: ActivityQuestion
}

export const QuestionFeedback = ({
  feedback,
  frozenAnswer,
  question,
}: QuestionFeedbackProps) => {
  const { feedbackElementRef } = useQuestionFeedback({ question })
  const scoreClassName =
    Number(feedback.score ?? 0) >= 80 ? 'text-success' : 'text-selo-text'

  return (
    <section
      aria-label='Resultado'
      aria-live='polite'
      className='question-feedback-session scroll-mt-6 mt-6 space-y-4 rounded-lg border border-border bg-card p-4 shadow-card sm:p-5'
      ref={feedbackElementRef}
    >
      <header className='flex flex-wrap items-start justify-between gap-3 border-b border-border pb-4'>
        <div className='space-y-1'>
          <p className='font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-success'>
            Feedback da questão
          </p>
          <h2 className='font-serif text-2xl leading-none text-foreground'>Resultado</h2>
        </div>
      </header>
      {feedback.status === 'inconclusive' ? (
        <p className='rounded-md border border-selo-text/40 bg-accent/50 p-3 text-sm text-selo-text'>
          Não foi possível concluir esta avaliação. Reavalie a mesma resposta.
        </p>
      ) : (
        <>
          <p className={`text-sm font-medium ${scoreClassName}`}>
            Pontuação: <span className='font-mono'>{feedback.score ?? 0}%</span>
          </p>
          <p className='text-sm leading-6 text-muted-foreground'>
            Essa pontuação considera somente esta questão. O comentário abaixo explica o
            que revisar; a nota final da Atividade será calculada após o envio das
            respostas.
          </p>
        </>
      )}
      {feedback.explanation ? (
        <p className='rounded-md border border-border/70 bg-muted/60 p-3 text-sm leading-6 text-foreground'>
          {feedback.explanation}
        </p>
      ) : null}
      {feedback.criteria?.length ? (
        <ul aria-label='Critérios avaliados' className='space-y-2'>
          {feedback.criteria.map((criterion, index) => {
            const criterionTitle =
              question.kind === 'javascript_stdin'
                ? question.criteria.find(({ key }) => key === criterion.key)?.name
                : undefined
            const scoreClassName =
              Number(criterion.level) >= 80 ? 'text-success' : 'text-amber-300'

            return (
              <li
                className='question-feedback-criterion rounded-md border border-border bg-surface-alt p-4 transition-colors hover:border-control-border'
                key={criterion.key}
                style={{ '--stagger-index': index } as CSSProperties}
              >
                <div className='flex items-start justify-between gap-4'>
                  <div className='min-w-0'>
                    <strong className='block text-sm font-medium text-foreground'>
                      {criterionTitle ?? 'Critério avaliado'}
                    </strong>
                    <span className='mt-1 block font-mono text-[10px] tracking-wide text-muted-foreground'>
                      Peso {criterion.weightPercentage}%
                    </span>
                  </div>
                  <output
                    aria-label={`Nível ${criterion.level} de 100`}
                    className={`shrink-0 font-mono text-lg font-semibold ${scoreClassName}`}
                  >
                    {criterion.level}/100
                  </output>
                </div>
                <p className='mt-3 text-sm leading-5 text-muted-foreground'>
                  {criterion.comment}
                </p>
              </li>
            )
          })}
        </ul>
      ) : null}
      {frozenAnswer?.kind === 'javascript_stdin' ? (
        <details>
          <summary className='cursor-pointer font-medium text-foreground underline-offset-4 hover:underline'>
            Arquivos avaliados
          </summary>
          {(feedback.submittedFiles ?? frozenAnswer.files).map((file) => (
            <div key={file.path} className='mt-3'>
              <h3 className='text-sm font-semibold'>{file.path}</h3>
              <pre className='overflow-x-auto rounded-md bg-muted p-3 text-xs'>
                {file.content}
              </pre>
            </div>
          ))}
        </details>
      ) : null}
    </section>
  )
}
