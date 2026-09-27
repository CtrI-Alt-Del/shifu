import { Checkbox } from '@/ui/shadcn/checkbox'
import { RadioGroup, RadioGroupItem } from '@/ui/shadcn/radio-group'
import { QuestionPrompt } from '@/ui/learning/widgets/components/question-prompt'

import { ActivityQuestionHeader } from '../components/activity-question-header'
import type { ChoiceQuestionProps } from '../use-activity-page'

import './choice-question.css'

export const ChoiceQuestion = ({
  disabled = false,
  activityTitle,
  difficulty,
  onToggleOption,
  question,
  questionNumber,
  selectedOptionKeys,
  totalQuestions,
}: ChoiceQuestionProps) => {
  const questionLabelId = `choice-question-${question.key}`

  return (
    <section aria-labelledby={questionLabelId} className='space-y-6'>
      <ActivityQuestionHeader
        activityTitle={activityTitle}
        difficulty={difficulty}
        questionContext={
          question.kind === 'multiple_selection'
            ? 'selecione todas as corretas'
            : 'escolha uma alternativa'
        }
        questionNumber={questionNumber}
        totalQuestions={totalQuestions}
      />
      <div className='choice-question-prompt'>
        <QuestionPrompt id={questionLabelId} prompt={question.prompt} />
      </div>

      {question.kind === 'single_choice' ? (
        <RadioGroup
          aria-labelledby={questionLabelId}
          className='choice-question-options space-y-2'
          disabled={disabled}
          name={`choice-${question.key}`}
          onValueChange={onToggleOption}
          value={selectedOptionKeys[0] ?? ''}
        >
          {question.options.map((option) => (
            <RadioGroupItem
              className='choice-question-option'
              key={option.key}
              disabled={disabled}
              label={option.text}
              value={option.key}
            />
          ))}
        </RadioGroup>
      ) : (
        <fieldset
          aria-labelledby={questionLabelId}
          className='choice-question-options space-y-2'
        >
          {question.options.map((option) => (
            <Checkbox
              className='choice-question-option'
              key={option.key}
              checked={selectedOptionKeys.includes(option.key)}
              disabled={disabled}
              label={option.text}
              onCheckedChange={() => onToggleOption(option.key)}
            />
          ))}
        </fieldset>
      )}
    </section>
  )
}
