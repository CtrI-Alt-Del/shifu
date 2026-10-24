import { useId } from 'react'

import { Button } from '@/ui/shadcn/button'

export type ObjectivePickerProps = {
  candidates: {
    goalId: string
    title: string
    isDisabled: boolean
    isSelected: boolean
  }[]
  hint: string
  onSelect: (goalId: string) => void
}

export const ObjectivePicker = ({ candidates, hint, onSelect }: ObjectivePickerProps) => {
  const labelId = useId()
  const hintId = useId()
  const reasonIdPrefix = useId()

  return (
    <div
      aria-describedby={hintId}
      aria-labelledby={labelId}
      className='flex flex-col items-start gap-2.5 max-[480px]:items-stretch'
      role='group'
    >
      <p
        className='text-[13px] font-medium leading-normal text-secondary-foreground'
        id={labelId}
      >
        Objetivo
      </p>
      <div className='flex flex-wrap items-start gap-2 max-[480px]:flex-col max-[480px]:items-stretch'>
        {candidates.map((candidate) => (
          <Button
            aria-describedby={
              candidate.isDisabled ? `${reasonIdPrefix}-${candidate.goalId}` : undefined
            }
            aria-disabled={candidate.isDisabled || undefined}
            aria-pressed={candidate.isSelected}
            className='h-auto min-h-11 flex-col items-start gap-0.5 whitespace-normal border border-control-border! py-2 text-left text-sm font-medium text-foreground! aria-disabled:cursor-not-allowed aria-disabled:opacity-50 max-[480px]:w-full'
            key={candidate.goalId}
            onClick={() => {
              if (!candidate.isDisabled) onSelect(candidate.goalId)
            }}
            type='button'
            variant='ghost'
          >
            <span className='break-words'>{candidate.title}</span>
            {candidate.isDisabled ? (
              <span
                className='text-xs font-normal text-muted-foreground'
                id={`${reasonIdPrefix}-${candidate.goalId}`}
              >
                Já contém esta Habilidade
              </span>
            ) : null}
          </Button>
        ))}
      </div>
      <p className='text-[13px] leading-normal text-secondary-foreground' id={hintId}>
        {hint}
      </p>
    </div>
  )
}
