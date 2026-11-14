import type { CSSProperties } from 'react'

import type { PlannerStep, PlannerStepState } from '../use-planner-page'

export type PlanningStepTrailProps = {
  label: string
  steps: PlannerStep[]
  disabled?: boolean
  onSelectStep: (index: number) => void
}

const STATE_LABELS: Record<PlannerStepState, string> = {
  current: 'Atual',
  answered: 'Respondida',
  pending: 'Pendente',
}

export const PlanningStepTrail = ({
  label,
  steps,
  disabled = false,
  onSelectStep,
}: PlanningStepTrailProps) => {
  return (
    <nav aria-label='Perguntas deste conjunto' className='flex flex-col gap-2'>
      <p
        aria-live='polite'
        className='text-[13px] leading-[1.45] text-secondary-foreground'
      >
        {label}
      </p>
      <ol
        className='grid gap-2'
        style={
          {
            gridTemplateColumns: `repeat(${Math.max(steps.length, 1)}, minmax(0, 1fr))`,
          } as CSSProperties
        }
      >
        {steps.map((step) => (
          <li key={step.questionId}>
            <button
              aria-current={step.state === 'current' ? 'step' : undefined}
              className={`flex min-h-11 w-full items-center rounded-md border border-control-border px-2.5 text-left text-xs font-semibold leading-tight text-foreground transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60 ${
                step.state === 'current' ? 'bg-muted' : 'bg-card'
              }`}
              disabled={disabled}
              onClick={() => onSelectStep(step.number - 1)}
              type='button'
            >
              {step.number} · {STATE_LABELS[step.state]}
            </button>
          </li>
        ))}
      </ol>
    </nav>
  )
}
