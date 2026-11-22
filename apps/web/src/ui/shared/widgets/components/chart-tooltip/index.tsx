import type { ChartDatum } from '@/ui/shared/widgets/components/chart-frame'

// The shape Recharts hands to a custom tooltip, reduced to what is rendered.
export type ChartTooltipProps = {
  active?: boolean
  payload?: ReadonlyArray<{ payload?: ChartDatum }>
}

// <output> is the native role='status' live region. Screen readers announce each
// point the arrow keys reach, so it carries only the label, the value and the note.
export const ChartTooltip = ({ active, payload }: ChartTooltipProps) => {
  const datum = active ? payload?.[0]?.payload : undefined

  return (
    <output aria-live='assertive'>
      {datum ? (
        <div className='rounded-md border border-border bg-card px-3 py-2 text-sm text-foreground'>
          <p className='font-semibold'>{datum.label}</p>
          <p className='tabular-nums'>{datum.valueLabel}</p>
          {datum.note ? <p className='text-muted-foreground'>{datum.note}</p> : null}
        </div>
      ) : null}
    </output>
  )
}
