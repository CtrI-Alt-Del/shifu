import type { ReactNode } from 'react'

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/ui/shadcn/tabs'

import { useChartFrame } from './use-chart-frame'

export type ChartDatum = {
  key: string
  label: string // axis label, e.g. '16 nov'
  value: number
  valueLabel: string // accessible value, e.g. '8 atividades'
  note?: string // e.g. 'Parcial'
}

export type ChartFrameProps = {
  title: string
  description: string // visible text summary
  emptyMessage?: string // shown instead of the switch and chart when present
  action?: ReactNode // own row under the header, e.g. the Habilidade select
  headerAction?: ReactNode // in the header beside the switch, e.g. a link
  footnote?: string // visible in both views, under the chart or the table
  columns: [string, string, ...string[]] // table headers
  rows: ChartDatum[]
  children: ReactNode // the chart
}

// 44 px touch targets as drawn in the boards; the primitive defaults to 36 px.
const SWITCH_LIST_CLASS_NAME = 'self-start gap-0! p-0! min-h-11! overflow-hidden'
const SWITCH_TRIGGER_CLASS_NAME = 'min-h-11! min-w-11 px-2.5!'

export const ChartFrame = ({
  title,
  description,
  emptyMessage,
  action,
  headerAction,
  footnote,
  columns,
  rows,
  children,
}: ChartFrameProps) => {
  const { headingId, view, handleViewChange } = useChartFrame()

  return (
    <section
      aria-labelledby={headingId}
      className='flex h-full min-w-0 flex-col gap-4 rounded-[14px] border border-border bg-surface-alt p-5'
    >
      <Tabs
        className='flex min-w-0 flex-col gap-4'
        onValueChange={handleViewChange}
        value={view}
      >
        {/* On a narrow screen the title shares its row with the header action and the
            switch drops to its own row; from `sm` on, all three share one row. */}
        <div className='flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4'>
          <div className='flex items-center justify-between gap-3 sm:contents'>
            <h3
              className='text-base font-semibold text-foreground sm:flex-1'
              id={headingId}
            >
              {title}
            </h3>
            {headerAction}
          </div>
          {emptyMessage ? null : (
            <TabsList
              aria-label={`Visualização de ${title}`}
              className={SWITCH_LIST_CLASS_NAME}
            >
              <TabsTrigger className={SWITCH_TRIGGER_CLASS_NAME} value='chart'>
                Gráfico
              </TabsTrigger>
              <TabsTrigger className={SWITCH_TRIGGER_CLASS_NAME} value='table'>
                Tabela
              </TabsTrigger>
            </TabsList>
          )}
        </div>
        {action ? <div className='min-w-0'>{action}</div> : null}
        <p className='text-sm text-secondary-foreground'>{description}</p>
        {emptyMessage ? (
          <p className='rounded-md border border-dashed border-border px-4 py-6 text-center text-sm text-muted-foreground'>
            {emptyMessage}
          </p>
        ) : (
          <>
            {/* The chart surface is already a tab stop, so the panel itself is not one. */}
            <TabsContent className='min-w-0' tabIndex={-1} value='chart'>
              {children}
            </TabsContent>
            <TabsContent className='min-w-0 overflow-x-auto' value='table'>
              <table className='w-full border-collapse text-left text-sm'>
                <caption className='sr-only'>{title}</caption>
                <thead>
                  <tr className='border-b border-border text-muted-foreground'>
                    {columns.map((column) => (
                      <th className='py-2 pr-4 font-semibold' key={column} scope='col'>
                        {column}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr className='border-b border-border last:border-b-0' key={row.key}>
                      <th className='py-2 pr-4 font-normal text-foreground' scope='row'>
                        {row.label}
                      </th>
                      <td className='py-2 pr-4 text-foreground tabular-nums'>
                        {row.valueLabel}
                      </td>
                      {columns.length > 2 ? (
                        <td className='py-2 pr-4 text-muted-foreground'>
                          {row.note ?? '—'}
                        </td>
                      ) : null}
                    </tr>
                  ))}
                </tbody>
              </table>
            </TabsContent>
            {footnote ? (
              <p className='text-[13px] text-secondary-foreground'>{footnote}</p>
            ) : null}
          </>
        )}
      </Tabs>
    </section>
  )
}
