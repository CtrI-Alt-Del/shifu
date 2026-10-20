import type { RefObject } from 'react'

import type { PlanningQuestion } from '@/core/intelligence/planning-session'
import { Checkbox } from '@/ui/shadcn/checkbox'
import { RadioGroup, RadioGroupItem } from '@/ui/shadcn/radio-group'

export type PlanningQuestionCardProps = {
  question: PlanningQuestion
  selectedOptionIds: string[]
  guidance: string
  headingRef: RefObject<HTMLHeadingElement | null>
  disabled?: boolean
  onSelectSingle: (optionId: string) => void
  onToggleMultiple: (optionId: string, checked: boolean) => void
}

export const PlanningQuestionCard = ({
  question,
  selectedOptionIds,
  guidance,
  headingRef,
  disabled = false,
  onSelectSingle,
  onToggleMultiple,
}: PlanningQuestionCardProps) => {
  const headingId = `planning-question-${question.id}`
  const guidanceId = `${headingId}-guidance`

  return (
    <section aria-labelledby={headingId} className='flex flex-col gap-6'>
      <h1
        className='font-serif text-3xl leading-[1.3] text-foreground outline-none focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-selo-text lg:text-4xl'
        id={headingId}
        ref={headingRef}
        tabIndex={-1}
      >
        {question.text}
      </h1>
      <p className='text-[13px] leading-[1.45] text-muted-foreground' id={guidanceId}>
        {guidance}
      </p>
      {question.kind === 'single' ? (
        <RadioGroup
          aria-describedby={guidanceId}
          aria-labelledby={headingId}
          className='planner-options flex flex-col gap-1.5'
          disabled={disabled}
          name={`planning-question-${question.id}`}
          onValueChange={onSelectSingle}
          value={selectedOptionIds[0] ?? ''}
        >
          {question.options.map((option) => (
            <RadioGroupItem
              className={`planner-option${option.exclusive ? ' planner-option--exclusive' : ''}`}
              key={option.id}
              label={option.text}
              value={option.id}
            />
          ))}
        </RadioGroup>
      ) : (
        <fieldset
          aria-describedby={guidanceId}
          aria-labelledby={headingId}
          className='planner-options flex flex-col gap-1.5'
        >
          {question.options.map((option) => (
            <Checkbox
              checked={selectedOptionIds.includes(option.id)}
              className={`planner-option${option.exclusive ? ' planner-option--exclusive' : ''}`}
              disabled={disabled}
              key={option.id}
              label={option.text}
              onCheckedChange={(checked) => onToggleMultiple(option.id, checked)}
            />
          ))}
        </fieldset>
      )}
    </section>
  )
}
