import {
  Area,
  CartesianGrid,
  ComposedChart,
  LabelList,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { useReducedMotionPreference } from '@/ui/shared/hooks/use-reduced-motion-preference'
import type { ChartDatum } from '@/ui/shared/widgets/components/chart-frame'
import { ChartTooltip } from '@/ui/shared/widgets/components/chart-tooltip'
import { ChartValueLabel } from '@/ui/shared/widgets/components/chart-value-label'

import { ChartDot } from './chart-dot'

export type LineChartProps = {
  data: ChartDatum[]
  tone: 'jade'
  title: string
  baselineLabel?: string // e.g. 'Ponto de partida · 42%'
}

const CHART_HEIGHT = 200
const PARTIAL_NOTE = 'Parcial'
const PERCENT_TICKS = [0, 50, 100]
const AXIS_TICK = { fill: 'var(--muted-foreground)', fontSize: 12 }
const ACTIVE_DOT = {
  r: 6,
  fill: 'var(--jade-text)',
  stroke: 'var(--card)',
  strokeWidth: 2,
}

export const LineChart = ({ data, title, baselineLabel }: LineChartProps) => {
  const { prefersReducedMotion } = useReducedMotionPreference()
  const lastIndex = data.length - 1
  const baselineValue = data[0]?.value

  return (
    <div className='[&_.recharts-surface]:overflow-visible'>
      <ResponsiveContainer height={CHART_HEIGHT} width='100%'>
        <ComposedChart
          aria-label={title}
          data={data}
          margin={{ top: 24, right: 8, bottom: 0, left: 0 }}
        >
          <CartesianGrid stroke='var(--border)' vertical={false} />
          <XAxis
            axisLine={false}
            dataKey='key'
            interval='preserveStartEnd'
            padding={{ left: 32, right: 32 }}
            tick={AXIS_TICK}
            tickFormatter={(key: string) =>
              data.find((datum) => datum.key === key)?.label ?? key
            }
            tickLine={false}
          />
          <YAxis
            axisLine={false}
            domain={[0, 100]}
            tick={AXIS_TICK}
            tickFormatter={(value: number) => `${value}%`}
            tickLine={false}
            ticks={PERCENT_TICKS}
            width={44}
          />
          {baselineLabel && baselineValue !== undefined ? (
            <ReferenceLine
              label={{
                value: baselineLabel,
                position: 'insideBottomLeft',
                dx: 28,
                dy: 22,
                fill: 'var(--muted-foreground)',
                fontSize: 12,
              }}
              stroke='var(--muted-foreground)'
              strokeOpacity={0.6}
              y={baselineValue}
            />
          ) : null}
          <Tooltip
            content={<ChartTooltip />}
            cursor={{ stroke: 'var(--border)' }}
            isAnimationActive={false}
          />
          <Area
            activeDot={false}
            dataKey='value'
            dot={false}
            fill='var(--jade-text)'
            fillOpacity={0.1}
            isAnimationActive={!prefersReducedMotion}
            stroke='none'
            tooltipType='none'
            type='monotone'
          />
          <Line
            activeDot={ACTIVE_DOT}
            dataKey='value'
            dot={({ cx, cy, index }) => (
              <ChartDot
                cx={cx}
                cy={cy}
                isLast={index === lastIndex}
                isPartial={data[index]?.note === PARTIAL_NOTE}
                key={data[index]?.key ?? index}
              />
            )}
            isAnimationActive={!prefersReducedMotion}
            stroke='var(--jade-text)'
            strokeWidth={2}
            type='monotone'
          >
            <LabelList
              content={<ChartValueLabel lift={10} />}
              position='top'
              valueAccessor={(_entry, index) =>
                index === lastIndex ? data[lastIndex]?.valueLabel : undefined
              }
            />
          </Line>
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
