import { motion } from 'motion/react'

import { ENTRANCE_RISE } from '@/constants/motion-variants'
import type {
  ImageChoiceQuestion as ImageChoiceQuestionData,
  PreliminaryQuestionResult,
} from '@/core/learning/choice-activity'
import type { ActivityDifficulty } from '@/core/learning/competency-detail'
import { ImageChoiceOptions } from '@/ui/learning/widgets/components/image-choice-options'
import { QuestionPrompt } from '@/ui/learning/widgets/components/question-prompt'

import { ActivityQuestionHeader } from '../components/activity-question-header'

export type ImageChoiceQuestionProps = {
  question: ImageChoiceQuestionData
  questionNumber: number
  totalQuestions: number
  selectedOptionKey: string | null
  feedback: PreliminaryQuestionResult | null
  onSelectOption: (optionKey: string) => void
  disabled?: boolean
  activityTitle?: string
  difficulty?: ActivityDifficulty
}

export const ImageChoiceQuestion = ({
  question,
  questionNumber,
  totalQuestions,
  selectedOptionKey,
  feedback,
  onSelectOption,
  disabled = false,
  activityTitle,
  difficulty,
}: ImageChoiceQuestionProps) => {
  const questionLabelId = `image-choice-question-${question.key}`
  const isVerified = feedback?.status === 'conclusive'

  return (
    <section aria-labelledby={questionLabelId} className='space-y-6'>
      <ActivityQuestionHeader
        activityTitle={activityTitle}
        difficulty={difficulty}
        questionContext='escolha uma imagem'
        questionNumber={questionNumber}
        totalQuestions={totalQuestions}
      />
      <motion.div variants={ENTRANCE_RISE}>
        <QuestionPrompt id={questionLabelId} prompt={question.prompt} />
      </motion.div>
      <motion.div variants={ENTRANCE_RISE}>
        <ImageChoiceOptions
          disabled={disabled}
          isCorrect={feedback?.isCorrect}
          labelledBy={questionLabelId}
          name={`image-choice-${question.key}`}
          onSelectOption={onSelectOption}
          options={question.options}
          selectedOptionKey={selectedOptionKey}
          state={isVerified ? 'verified' : 'selecting'}
        />
      </motion.div>
    </section>
  )
}
