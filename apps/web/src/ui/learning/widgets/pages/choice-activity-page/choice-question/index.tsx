import { Checkbox } from '@/ui/shadcn/checkbox'
import { RadioGroup, RadioGroupItem } from '@/ui/shadcn/radio-group'
import { QuestionPrompt } from '@/ui/learning/widgets/components/question-prompt'

import type { ChoiceQuestionProps } from '../use-choice-activity-page'

import './choice-question.css'

export const ChoiceQuestion = ({
  disabled = false,
  difficultyLabel,
  onToggleOption,
  question,
  questionNumber,
  selectedOptionKeys,
  totalQuestions,
}: ChoiceQuestionProps) => {
  const questionLabelId = `choice-question-${question.key}`

  return (
    <section aria-labelledby={questionLabelId} className='space-y-6'>
      <div className='space-y-5'>
        <div className='flex flex-wrap items-center justify-between gap-x-4 gap-y-2'>
          {difficultyLabel ? (
            <span className='rounded-md bg-success/15 px-2 py-1 text-xs font-medium text-success'>
              {difficultyLabel}
            </span>
          ) : null}
          <p className='text-sm text-muted-foreground'>
            <span>
              Questão {questionNumber} de {totalQuestions}
            </span>
            <span aria-hidden='true'> · </span>
            <span>
              {question.kind === 'multiple_selection'
                ? 'selecione todas as corretas'
                : 'escolha uma alternativa'}
            </span>
          </p>
        </div>
        <div className='choice-question-prompt'>
          <QuestionPrompt id={questionLabelId} prompt={question.prompt} />
        </div>
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
