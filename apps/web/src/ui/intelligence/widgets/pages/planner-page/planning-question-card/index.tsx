import type { RefObject } from 'react'

import {
  PLANNING_OTHER_TEXT_MAX_LENGTH,
  type PlanningQuestion,
} from '@/core/intelligence/planning-session'
import { Checkbox } from '@/ui/shadcn/checkbox'
import { Label } from '@/ui/shadcn/label'
import { RadioGroup, RadioGroupItem } from '@/ui/shadcn/radio-group'
import { Textarea } from '@/ui/shadcn/textarea'

export type PlanningQuestionCardProps = {
  question: PlanningQuestion
  selectedOptionIds: string[]
  otherText: string
  isOtherSelected: boolean
  guidance: string
  headingRef: RefObject<HTMLHeadingElement | null>
  disabled?: boolean
  onSelectSingle: (optionId: string) => void
  onToggleMultiple: (optionId: string, checked: boolean) => void
  onChangeOtherText: (text: string) => void
}

// A stable callback ref focuses the field only when it appears.
const focusOnMount = (node: HTMLTextAreaElement | null) => node?.focus()

export const PlanningQuestionCard = ({
  question,
  selectedOptionIds,
  otherText,
  isOtherSelected,
  guidance,
  headingRef,
  disabled = false,
  onSelectSingle,
  onToggleMultiple,
  onChangeOtherText,
}: PlanningQuestionCardProps) => {
  const headingId = `planning-question-${question.id}`
  const guidanceId = `${headingId}-guidance`
  const otherFieldId = `${headingId}-other`
  const otherCountId = `${otherFieldId}-count`

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
      {isOtherSelected ? (
        <div className='flex flex-col gap-1.5'>
          <Label
            className='text-[13px] font-semibold text-secondary-foreground'
            htmlFor={otherFieldId}
          >
            Descreva sua resposta
          </Label>
          <Textarea
            aria-describedby={otherCountId}
            className='min-h-[72px] resize-none px-4 py-3 text-[15px] leading-[1.45]'
            disabled={disabled}
            id={otherFieldId}
            maxLength={PLANNING_OTHER_TEXT_MAX_LENGTH}
            onChange={(event) => onChangeOtherText(event.target.value)}
            ref={focusOnMount}
            rows={2}
            value={otherText}
          />
          <p className='self-end text-xs text-muted-foreground' id={otherCountId}>
            {otherText.length}/{PLANNING_OTHER_TEXT_MAX_LENGTH} caracteres
          </p>
        </div>
      ) : null}
    </section>
  )
}
