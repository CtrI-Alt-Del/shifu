import type { CSSProperties } from 'react'

import type {
  ActivityQuestion,
  ActivityAnswer,
  PreliminaryQuestionResult,
} from '@/core/learning/choice-activity'

import {
  PAIR_MATCHING_OUTCOME_ICONS,
  PAIR_MATCHING_OUTCOME_LABELS,
} from '@/core/learning/pair-matching-outcome'
import { Icon } from '@/ui/shared/widgets/components/icon'

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
  const { feedbackElementRef, fillBlanksOutcome } = useQuestionFeedback({
    feedback,
    question,
  })
  const scoreClassName =
    Number(feedback.score ?? 0) >= 80 ? 'text-success' : 'text-selo-text'

  return (
    <section
      aria-label='Resultado'
      aria-live={question.kind === 'fill_blanks' ? undefined : 'polite'}
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
      {question.kind === 'pair_matching' && feedback.outcome ? (
        <p className='flex flex-wrap items-center gap-2 text-sm font-medium text-foreground'>
          <Icon className='size-5' name={PAIR_MATCHING_OUTCOME_ICONS[feedback.outcome]} />
          <span>{PAIR_MATCHING_OUTCOME_LABELS[feedback.outcome]}</span>
          <span className='font-normal text-muted-foreground'>
            {feedback.correctPairCount ?? 0} de {feedback.totalPairCount ?? 0} pares
            corretos.
          </span>
        </p>
      ) : null}
      {fillBlanksOutcome ? (
        <p className='flex flex-wrap items-center gap-2 text-sm font-medium text-foreground'>
          <Icon aria-hidden='true' name={fillBlanksOutcome.iconName} size={16} />
          <span>{fillBlanksOutcome.label}</span>
          <span aria-hidden='true' className='text-muted-foreground'>
            ·
          </span>
          <span className='text-muted-foreground'>{fillBlanksOutcome.countText}</span>
        </p>
      ) : null}
      {feedback.explanation ? (
        <p className='rounded-md border border-border/70 bg-muted/60 p-3 text-sm leading-6 text-foreground'>
          {feedback.explanation}
        </p>
      ) : null}
      {feedback.criteria?.length ? (
        <ul aria-label='Critérios avaliados' className='space-y-2'>
          {feedback.criteria.map((criterion, index) => {
            const criterionTitle =
              question.kind === 'javascript_stdin' ||
              question.kind === 'react' ||
              question.kind === 'html_css_js' ||
              question.kind === 'react_fastify' ||
              question.kind === 'translation'
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
      {frozenAnswer?.kind === 'javascript_stdin' ||
      frozenAnswer?.kind === 'react' ||
      frozenAnswer?.kind === 'html_css_js' ||
      frozenAnswer?.kind === 'react_fastify' ? (
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
      ) : frozenAnswer?.kind === 'pair_matching' && question.kind === 'pair_matching' ? (
        <div>
          <h3 className='text-sm font-semibold text-foreground'>Pares enviados</h3>
          <ul aria-label='Pares enviados' className='mt-2 space-y-1 text-sm'>
            {(feedback.submittedPairs ?? frozenAnswer.pairs).map((pair) => (
              <li key={pair.wordKey}>
                {question.words.find((word) => word.key === pair.wordKey)?.text ??
                  pair.wordKey}{' '}
                —{' '}
                {question.translations.find(
                  (translation) => translation.key === pair.translationKey,
                )?.text ?? pair.translationKey}
              </li>
            ))}
          </ul>
        </div>
      ) : frozenAnswer?.kind === 'translation' ? (
        <details>
          <summary className='cursor-pointer font-medium text-foreground underline-offset-4 hover:underline'>
            Texto avaliado
          </summary>
          <pre className='mt-3 overflow-x-auto rounded-md bg-muted p-3 text-xs whitespace-pre-wrap'>
            {feedback.submittedText ?? frozenAnswer.text}
          </pre>
        </details>
      ) : null}
    </section>
  )
}
