import type { PlanningProposal } from '@/core/intelligence/planning-session'
import { Button } from '@/ui/shadcn/button'

import { PlanningIntentSummary } from '../planning-intent-summary'

/**
 * Review boundary of the Planner: receives the validated proposal exactly as the
 * backend exposed it. SHIFU-93 owns the review rendering and replaces this body.
 */
export type PlanningProposalHandoffProps = {
  planningId: string
  intent: string
  proposal: PlanningProposal
  isCancelling: boolean
  onCancel: () => void
}

export const PlanningProposalHandoff = ({
  planningId,
  intent,
  proposal,
  isCancelling,
  onCancel,
}: PlanningProposalHandoffProps) => {
  const skillCount = proposal.skills.length
  const skillSummary =
    skillCount === 1
      ? '1 Habilidade do Currículo selecionada.'
      : `${skillCount} Habilidades do Currículo selecionadas.`

  return (
    <section
      aria-labelledby='planning-proposal-ready'
      className='flex flex-col gap-6'
      data-planning-id={planningId}
    >
      <div className='flex flex-col gap-2'>
        <p className='text-xs font-bold uppercase tracking-[0.16em] text-jade-text'>
          Proposta pronta
        </p>
        <h1
          className='font-serif text-3xl leading-[1.3] text-foreground lg:text-4xl'
          id='planning-proposal-ready'
        >
          Sua proposta está pronta para revisão
        </h1>
      </div>
      <PlanningIntentSummary intent={intent} />
      <output
        aria-live='polite'
        className='block rounded-[10px] border border-border bg-surface-alt p-4'
      >
        <span className='block text-xs font-medium leading-[1.45] text-muted-foreground'>
          Objetivo proposto
        </span>
        <span className='mt-2 block text-[15px] font-semibold leading-[1.45] text-foreground'>
          {proposal.title}
        </span>
        <span className='mt-1 block text-[13px] leading-[1.45] text-secondary-foreground'>
          {skillSummary} A revisão e a confirmação chegam na próxima etapa do Planejador.
        </span>
      </output>
      <div className='flex justify-center sm:justify-start'>
        <Button disabled={isCancelling} onClick={onCancel} type='button' variant='ghost'>
          Cancelar
        </Button>
      </div>
    </section>
  )
}
