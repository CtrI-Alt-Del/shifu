export type PlanningIntentSummaryProps = {
  intent: string
}

export const PlanningIntentSummary = ({ intent }: PlanningIntentSummaryProps) => {
  return (
    <section
      aria-label='Intenção do planejamento'
      className='rounded-[10px] border border-border bg-muted p-4'
    >
      <p className='text-xs font-medium leading-[1.45] text-muted-foreground'>
        O que você quer alcançar
      </p>
      <p className='mt-2 text-[15px] leading-[1.45] text-foreground'>{intent}</p>
    </section>
  )
}
