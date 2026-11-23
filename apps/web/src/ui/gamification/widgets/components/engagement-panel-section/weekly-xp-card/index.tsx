import { motion } from 'motion/react'

import { ENTRANCE_CARD } from '@/constants/motion-variants'
import { Anchor } from '@/ui/shared/widgets/components/anchor'
import { BarChart } from '@/ui/shared/widgets/components/bar-chart'
import { ChartFrame, type ChartDatum } from '@/ui/shared/widgets/components/chart-frame'

export type WeeklyXpCardProps = {
  weeks: ChartDatum[]
}

const TITLE = 'XP por semana'

// `ChartFrame` draws its own card surface, so this wrapper only animates it.
export const WeeklyXpCard = ({ weeks }: WeeklyXpCardProps) => (
  <motion.div variants={ENTRANCE_CARD}>
    <ChartFrame
      headerAction={
        <Anchor
          className='inline-flex min-h-11 items-center text-sm font-medium text-secondary-foreground underline underline-offset-2 hover:text-foreground lg:min-h-0'
          route='gamificationXpHistory'
        >
          Ver histórico de XP
        </Anchor>
      }
      columns={['Semana', 'XP']}
      description='Últimas 12 semanas · XP mede engajamento, não conhecimento'
      rows={weeks}
      title={TITLE}
    >
      <BarChart data={weeks} highlightLast title={TITLE} tone='latao' />
    </ChartFrame>
  </motion.div>
)
