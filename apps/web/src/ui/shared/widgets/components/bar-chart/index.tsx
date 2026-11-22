import {
  Bar,
  BarChart as RechartsBarChart,
  CartesianGrid,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { useReducedMotionPreference } from '@/ui/shared/hooks/use-reduced-motion-preference'
import type { ChartDatum } from '@/ui/shared/widgets/components/chart-frame'
import { ChartTooltip } from '@/ui/shared/widgets/components/chart-tooltip'
import { ChartValueLabel } from '@/ui/shared/widgets/components/chart-value-label'

export type BarChartProps = {
  data: ChartDatum[]
  tone: 'jade' | 'latao'
  title: string // accessible name of the chart surface
  highlightLast?: boolean // labels the last bar's value, as in the boards
}

const CHART_HEIGHT = 200
const BAR_FILL = { jade: 'var(--jade-solid)', latao: 'var(--latao-fill)' } as const
const AXIS_TICK = { fill: 'var(--muted-foreground)', fontSize: 12 }

export const BarChart = ({ data, tone, title, highlightLast = false }: BarChartProps) => {
  const { prefersReducedMotion } = useReducedMotionPreference()
  const lastIndex = data.length - 1

  return (
    <div className='[&_.recharts-surface]:overflow-visible'>
      <ResponsiveContainer height={CHART_HEIGHT} width='100%'>
        <RechartsBarChart
          aria-label={title}
          data={data}
          margin={{ top: 24, right: 8, bottom: 0, left: 0 }}
        >
          <CartesianGrid stroke='var(--border)' vertical={false} />
          <XAxis
            axisLine={false}
            dataKey='key'
            interval='preserveStartEnd'
            tick={AXIS_TICK}
            tickFormatter={(key: string) =>
              data.find((datum) => datum.key === key)?.label ?? key
            }
            tickLine={false}
          />
          <YAxis
            allowDecimals={false}
            axisLine={false}
            tick={AXIS_TICK}
            tickCount={4}
            tickLine={false}
            width={40}
          />
          <Tooltip
            content={<ChartTooltip />}
            cursor={{ fill: 'var(--muted)', opacity: 0.4 }}
            isAnimationActive={false}
          />
          <Bar
            dataKey='value'
            fill={BAR_FILL[tone]}
            isAnimationActive={!prefersReducedMotion}
            maxBarSize={24}
            radius={4}
          >
            {highlightLast ? (
              <LabelList
                content={<ChartValueLabel lift={4} />}
                position='top'
                valueAccessor={(_entry, index) =>
                  index === lastIndex ? data[lastIndex]?.valueLabel : undefined
                }
              />
            ) : null}
          </Bar>
        </RechartsBarChart>
      </ResponsiveContainer>
    </div>
  )
}
