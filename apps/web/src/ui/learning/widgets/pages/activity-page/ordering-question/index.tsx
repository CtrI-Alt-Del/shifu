import { closestCenter, DndContext } from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable'

import type { OrderingQuestion as OrderingQuestionData } from '@/core/learning/choice-activity'
import { QuestionPrompt } from '@/ui/learning/widgets/components/question-prompt'
import { Icon } from '@/ui/shared/widgets/components/icon'

import { ActivityQuestionHeader } from '../components/activity-question-header'
import { OrderingStep } from './ordering-step'
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

const SCREEN_READER_INSTRUCTIONS =
  'Para mover uma etapa com o teclado, use os botões Mover para cima e Mover para baixo.'

// The hook owns the single polite region, so the library announcements stay silent.
const ANNOUNCEMENTS = {
  onDragStart: () => undefined,
  onDragOver: () => undefined,
  onDragEnd: () => undefined,
  onDragCancel: () => undefined,
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
  const {
    announcement,
    order,
    sensors,
    handleDragCancel,
    handleDragEnd,
    handleDragStart,
    handleMoveStep,
    moveCount,
    sortableIds,
  } = useOrderingQuestion({
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
            A ordem exibida é apenas um ponto de partida. Arraste as etapas ou use os
            controles para organizá-las.
          </p>
        ) : null}
        <DndContext
          collisionDetection={closestCenter}
          accessibility={{
            announcements: ANNOUNCEMENTS,
            screenReaderInstructions: { draggable: SCREEN_READER_INSTRUCTIONS },
          }}
          onDragCancel={handleDragCancel}
          onDragEnd={handleDragEnd}
          onDragStart={handleDragStart}
          sensors={sensors}
        >
          <SortableContext items={sortableIds} strategy={verticalListSortingStrategy}>
            <ol aria-label='Etapas do procedimento' className='space-y-2'>
              {order.map((stepKey, index) => {
                const step = question.steps.find(({ key }) => key === stepKey)
                if (!step) return null
                return (
                  <OrderingStep
                    disabled={disabled}
                    isFirst={index === 0}
                    isLast={index === order.length - 1}
                    isVerified={isVerified}
                    key={step.key}
                    moveCount={moveCount}
                    onMove={handleMoveStep}
                    position={index + 1}
                    step={step}
                  />
                )
              })}
            </ol>
          </SortableContext>
        </DndContext>
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
