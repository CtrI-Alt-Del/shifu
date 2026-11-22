import { motion } from 'motion/react'

import { ENTRANCE_CARD, ENTRANCE_ROW } from '@/constants/motion-variants'
import type { RecentMastery } from '@/core/learning/learning-panorama'
import { useFormatDate } from '@/ui/shared/hooks/use-format-date'
import { Icon } from '@/ui/shared/widgets/components/icon'

export type RecentMasteriesCardProps = {
  masteries: RecentMastery[]
}

export const RecentMasteriesCard = ({ masteries }: RecentMasteriesCardProps) => {
  const { formatCompactDayLabel } = useFormatDate()

  return (
    <motion.section
      aria-labelledby='learning-panorama-masteries-title'
      className='flex min-w-0 flex-col gap-4 rounded-[14px] border border-border bg-surface-alt p-5'
      variants={ENTRANCE_CARD}
    >
      <h3
        className='text-base font-semibold text-foreground'
        id='learning-panorama-masteries-title'
      >
        Domínios recentes
      </h3>
      {masteries.length === 0 ? (
        <p className='text-sm text-muted-foreground'>
          Nenhuma Competência dominada recentemente.
        </p>
      ) : (
        <ul className='flex flex-col gap-3.5'>
          {masteries.map((mastery) => (
            <motion.li
              className='flex items-start gap-3'
              key={`${mastery.skillExperienceId}-${mastery.competencyId}`}
              variants={ENTRANCE_ROW}
            >
              <Icon
                className='mt-0.5 shrink-0 text-jade-solid'
                name='circle-check'
                size={18}
              />
              <span className='min-w-0 space-y-0.5'>
                <span className='block text-sm font-medium text-foreground'>
                  {mastery.competencyName}
                </span>
                <span className='block text-[13px] text-muted-foreground'>
                  {mastery.skillName} · {mastery.goalTitle} ·{' '}
                  {formatCompactDayLabel(mastery.masteredOn)}
                </span>
              </span>
            </motion.li>
          ))}
        </ul>
      )}
    </motion.section>
  )
}
