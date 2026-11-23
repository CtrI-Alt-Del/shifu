import { motion } from 'motion/react'

import { ENTRANCE_CARD } from '@/constants/motion-variants'
import { BarChart } from '@/ui/shared/widgets/components/bar-chart'
import { ChartFrame, type ChartDatum } from '@/ui/shared/widgets/components/chart-frame'

export type WeeklyEvaluationsCardProps = {
  data: ChartDatum[]
  hasData: boolean
}

const TITLE = 'Atividades avaliadas por semana'

export const WeeklyEvaluationsCard = ({ data, hasData }: WeeklyEvaluationsCardProps) => (
  <motion.div className='h-full min-w-0' variants={ENTRANCE_CARD}>
    <ChartFrame
      columns={['Semana iniciada em', 'Atividades avaliadas']}
      description='Últimas 8 semanas, em todas as suas Habilidades'
      emptyMessage={
        hasData
          ? undefined
          : 'As contagens semanais aparecerão depois das primeiras avaliações.'
      }
      footnote='O valor é uma contagem de atividades avaliadas e não representa desempenho.'
      rows={data}
      title={TITLE}
    >
      <BarChart data={data} highlightLast title={TITLE} tone='jade' />
    </ChartFrame>
  </motion.div>
)
