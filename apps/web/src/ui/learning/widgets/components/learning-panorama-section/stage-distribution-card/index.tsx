import { motion } from 'motion/react'

import { ENTRANCE_CARD } from '@/constants/motion-variants'
import { AnimatedNumber } from '@/ui/shared/widgets/components/animated-number'

export type StageItem = {
  key: 'not-started' | 'diagnosing' | 'learning' | 'completed'
  label: string
  count: number
}

export type StageDistributionCardProps = {
  summary: string
  items: StageItem[]
}

// The four stages share the jade family; "Não iniciadas" is outlined instead
// of filled, and every stage also carries its label and count in the legend.
const STAGE_CLASS_NAMES: Record<StageItem['key'], string> = {
  'not-started': 'border border-control-border!',
  diagnosing: 'bg-jade-fill',
  learning: 'bg-jade-solid',
  completed: 'bg-jade-text',
}

export const StageDistributionCard = ({ summary, items }: StageDistributionCardProps) => {
  const total = items.reduce((sum, item) => sum + item.count, 0)

  return (
    <motion.section
      aria-labelledby='learning-panorama-stages-title'
      className='flex min-w-0 flex-col gap-4 rounded-[14px] border border-border bg-surface-alt p-5'
      variants={ENTRANCE_CARD}
    >
      <h3
        className='text-base font-semibold text-foreground'
        id='learning-panorama-stages-title'
      >
        Habilidades por etapa
      </h3>
      <p className='text-[13px] text-secondary-foreground'>{summary}</p>
      <div aria-hidden='true' className='flex h-3 gap-0.5 overflow-hidden rounded'>
        {total === 0 ? (
          <span className='h-full w-full bg-muted' />
        ) : (
          items
            .filter((item) => item.count > 0)
            .map((item) => (
              <span
                className={`h-full min-w-1 rounded-[2px] ${STAGE_CLASS_NAMES[item.key]}`}
                key={item.key}
                style={{ flexGrow: item.count, flexBasis: 0 }}
              />
            ))
        )}
      </div>
      <ul className='flex flex-col gap-2.5'>
        {items.map((item) => (
          <li className='flex items-center gap-2.5 text-sm' key={item.key}>
            <span
              aria-hidden='true'
              className={`size-2.5 shrink-0 rounded-full ${STAGE_CLASS_NAMES[item.key]}`}
            />
            <span className='flex-1 text-secondary-foreground'>{item.label}</span>
            <AnimatedNumber
              className='font-mono font-semibold text-foreground'
              value={item.count}
            />
          </li>
        ))}
      </ul>
    </motion.section>
  )
}
