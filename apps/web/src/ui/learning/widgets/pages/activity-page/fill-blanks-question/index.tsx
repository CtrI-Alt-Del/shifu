import { DndContext } from '@dnd-kit/core'
import { motion } from 'motion/react'

import { ENTRANCE_RISE } from '@/constants/motion-variants'
import type { ActivityDifficulty } from '@/core/learning/competency-detail'
import type {
  FillBlanksPlacement,
  FillBlanksQuestion as FillBlanksQuestionContent,
} from '@/core/learning/choice-activity'
import { QuestionPrompt } from '@/ui/learning/widgets/components/question-prompt'

import { ActivityQuestionHeader } from '../components/activity-question-header'
import { FillBlanksText } from './fill-blanks-text'
import { useFillBlanksQuestion } from './use-fill-blanks-question'
import { WordBank } from './word-bank'

import './fill-blanks-question.css'

export type FillBlanksQuestionProps = {
  activityTitle?: string
  difficulty?: ActivityDifficulty
  disabled?: boolean
  onPlacementsChange: (placements: readonly FillBlanksPlacement[]) => void
  placements: readonly FillBlanksPlacement[]
  question: FillBlanksQuestionContent
  questionNumber: number
  totalQuestions: number
}

const SCREEN_READER_INSTRUCTIONS =
  'Para colocar uma palavra com o teclado, selecione a palavra no banco e depois a lacuna.'

const ANNOUNCEMENTS = {
  onDragStart: () => 'Arrastando a palavra. Solte sobre uma lacuna.',
  onDragOver: () => undefined,
  onDragEnd: () => 'Palavra solta.',
  onDragCancel: () => 'Arrasto cancelado.',
}

export const FillBlanksQuestion = (props: FillBlanksQuestionProps) => {
  const {
    activityTitle,
    difficulty,
    disabled = false,
    question,
    questionNumber,
    totalQuestions,
  } = props
  const {
    announcement,
    availableWords,
    blankNumberByKey,
    filledBlankCount,
    placedWordKeyByBlank,
    selectedWordKey,
    sensors,
    wordByKey,
    blankCount,
    handleBlankActivate,
    handleDragCancel,
    handleDragEnd,
    handleDragStart,
    handleWordSelect,
  } = useFillBlanksQuestion(props)
  const questionLabelId = `fill-blanks-question-${question.key}`
  const instructionsId = `fill-blanks-instructions-${question.key}`

  return (
    <DndContext
      accessibility={{
        announcements: ANNOUNCEMENTS,
        screenReaderInstructions: { draggable: SCREEN_READER_INSTRUCTIONS },
      }}
      onDragCancel={handleDragCancel}
      onDragEnd={handleDragEnd}
      onDragStart={handleDragStart}
      sensors={sensors}
    >
      <section
        aria-describedby={instructionsId}
        aria-labelledby={questionLabelId}
        className='space-y-6'
      >
        <ActivityQuestionHeader
          activityTitle={activityTitle}
          difficulty={difficulty}
          questionContext='preencha as lacunas'
          questionNumber={questionNumber}
          totalQuestions={totalQuestions}
        />
        <motion.div variants={ENTRANCE_RISE}>
          <QuestionPrompt id={questionLabelId} prompt={question.prompt} />
        </motion.div>
        <motion.div className='space-y-4' variants={ENTRANCE_RISE}>
          <p className='text-sm text-muted-foreground' id={instructionsId}>
            Arraste uma palavra até a lacuna ou selecione a palavra e depois a lacuna.
            Selecione uma lacuna preenchida para devolver a palavra ao banco.
          </p>
          <FillBlanksText
            blankNumberByKey={blankNumberByKey}
            contentLanguage={question.contentLanguage}
            disabled={disabled}
            onActivateBlank={handleBlankActivate}
            placedWordKeyByBlank={placedWordKeyByBlank}
            segments={question.segments}
            wordByKey={wordByKey}
          />
          <WordBank
            contentLanguage={question.contentLanguage}
            disabled={disabled}
            onSelectWord={handleWordSelect}
            selectedWordKey={selectedWordKey}
            words={availableWords}
          />
          <p className='text-sm text-muted-foreground'>
            {filledBlankCount} de {blankCount} lacunas preenchidas
          </p>
        </motion.div>
        <output aria-live='polite' className='sr-only'>
          {announcement}
        </output>
      </section>
    </DndContext>
  )
}
