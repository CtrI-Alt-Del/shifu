import { Checkbox } from '@/ui/shadcn/checkbox'
import { RadioGroup, RadioGroupItem } from '@/ui/shadcn/radio-group'

import type { ChoiceQuestionProps } from '../use-choice-activity-page'

export const ChoiceQuestion = ({
  disabled = false,
  onToggleOption,
  question,
  questionNumber,
  selectedOptionKeys,
  totalQuestions,
}: ChoiceQuestionProps) => {
  const questionLabelId = `choice-question-${question.key}`

  return (
    <section aria-labelledby={questionLabelId} className='space-y-5'>
      <div className='space-y-2'>
        <p className='text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground'>
          Questão {questionNumber} de {totalQuestions}
        </p>
        <h2
          className='whitespace-pre-wrap font-serif text-2xl leading-tight text-foreground sm:text-3xl'
          id={questionLabelId}
        >
          {question.prompt}
        </h2>
      </div>

      {question.kind === 'single_choice' ? (
        <RadioGroup
          aria-labelledby={questionLabelId}
          className='space-y-2'
          disabled={disabled}
          name={`choice-${question.key}`}
          onValueChange={onToggleOption}
          value={selectedOptionKeys[0] ?? ''}
        >
          {question.options.map((option) => (
            <RadioGroupItem
              key={option.key}
              disabled={disabled}
              label={option.text}
              value={option.key}
            />
          ))}
        </RadioGroup>
      ) : (
        <fieldset aria-labelledby={questionLabelId} className='space-y-2'>
          {question.options.map((option) => (
            <Checkbox
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
