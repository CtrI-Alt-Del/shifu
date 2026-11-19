import { motion } from 'motion/react'

import type { OrderingQuestion as OrderingQuestionData } from '@/core/learning/choice-activity'
import { ENTRANCE_RISE } from '@/constants/motion-variants'
import { Button } from '@/ui/shadcn/button'
import { QuestionPrompt } from '@/ui/learning/widgets/components/question-prompt'
import { Icon } from '@/ui/shared/widgets/components/icon'

import { ActivityQuestionHeader } from '../components/activity-question-header'
import { useOrderingQuestion } from './use-ordering-question'

export type OrderingQuestionProps = {
  question: OrderingQuestionData
  questionNumber: number
  totalQuestions: number
  disabled?: boolean
  isVerified?: boolean
  isCorrect?: boolean
  activityTitle?: string
  orderedStepKeys: readonly string[]
  onOrderChange?: (orderedStepKeys: readonly string[]) => void
}

export const OrderingQuestion = ({
  activityTitle,
  disabled = false,
  isVerified = false,
  isCorrect,
  onOrderChange,
  orderedStepKeys,
  question,
  questionNumber,
  totalQuestions,
}: OrderingQuestionProps) => {
  const questionLabelId = `ordering-question-${question.key}`
  const { announcement, handleMoveStep, order } = useOrderingQuestion({
    question,
    orderedStepKeys,
    disabled: disabled || isVerified,
    onOrderChange,
  })

  return (
    <section aria-labelledby={questionLabelId} className='space-y-6'>
      <ActivityQuestionHeader
        activityTitle={activityTitle}
        questionContext='organize as etapas'
        questionNumber={questionNumber}
        totalQuestions={totalQuestions}
        showQuestionProgress
      />
      <div className='space-y-3'>
        <QuestionPrompt id={questionLabelId} prompt={question.prompt} />
        {!isVerified ? (
          <p className='text-sm text-muted-foreground'>
            A ordem exibida é apenas um ponto de partida. Use os controles para organizar
            as etapas.
          </p>
        ) : null}
        <ol aria-label='Etapas do procedimento' className='space-y-2'>
          {order.map((stepKey, index) => {
            const step = question.steps.find(({ key }) => key === stepKey)
            if (!step) return null
            return (
              <motion.li
                className='flex min-h-14 items-center gap-3 rounded-md border border-control-border bg-card p-2 sm:p-3'
                key={step.key}
                variants={ENTRANCE_RISE}
              >
                <span
                  aria-hidden='true'
                  className='w-7 shrink-0 text-center font-mono text-sm text-muted-foreground'
                >
                  {index + 1}
                </span>
                <span className='min-w-0 flex-1 whitespace-pre-wrap text-sm'>
                  {step.text}
                </span>
                {!isVerified ? (
                  <span className='flex shrink-0 gap-1'>
                    <Button
                      aria-label={`Mover para cima: ${step.text}`}
                      className='h-11 w-11 min-h-11 px-0'
                      disabled={disabled || index === 0}
                      onClick={() => handleMoveStep(step.key, -1)}
                      type='button'
                      variant='outline'
                    >
                      <Icon name='arrow-up' size={18} />
                    </Button>
                    <Button
                      aria-label={`Mover para baixo: ${step.text}`}
                      className='h-11 w-11 min-h-11 px-0'
                      disabled={disabled || index === order.length - 1}
                      onClick={() => handleMoveStep(step.key, 1)}
                      type='button'
                      variant='outline'
                    >
                      <Icon className='rotate-180' name='arrow-up' size={18} />
                    </Button>
                  </span>
                ) : null}
              </motion.li>
            )
          })}
        </ol>
        {!isVerified ? (
          <p aria-live='polite' className='sr-only'>
            {announcement}
          </p>
        ) : null}
        {isVerified ? (
          <p className='flex items-center gap-2 text-sm text-muted-foreground'>
            <Icon
              name={
                (isCorrect ?? question.verified?.isCorrect)
                  ? 'circle-check'
                  : 'circle-alert'
              }
              size={16}
            />
            Ordem verificada. Somente leitura.
          </p>
        ) : null}
      </div>
    </section>
  )
}
