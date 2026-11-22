import { motion } from 'motion/react'

import { ENTRANCE_SECTION } from '@/constants/motion-variants'
import { SkillActionsMenu } from '@/ui/learning/widgets/components/skill-actions-menu'
import { Icon } from '@/ui/shared/widgets/components/icon'

export type SkillCompletionHeaderProps = {
  skillName: string
  statusLabel: string
  dateRange: string
  dateRangeLabel: string
  onRemove: (trigger: HTMLButtonElement) => void
}

export const SkillCompletionHeader = ({
  skillName,
  statusLabel,
  dateRange,
  dateRangeLabel,
  onRemove,
}: SkillCompletionHeaderProps) => {
  return (
    <motion.header
      className='grid grid-cols-[auto_1fr_auto] items-center gap-x-3 gap-y-3 lg:grid-cols-[1fr_auto_auto] lg:items-start'
      variants={ENTRANCE_SECTION}
    >
      <h1 className='col-span-2 min-w-0 font-serif text-[32px] leading-[1.2] text-foreground lg:col-span-1 lg:text-[40px] lg:leading-none'>
        {skillName}
      </h1>
      <span className='col-start-1 row-start-2 inline-flex items-center gap-2 justify-self-start rounded-md bg-jade-fill px-3 py-1 text-xs font-semibold leading-4 text-background'>
        <Icon name='circle-check' size={12} />
        {statusLabel}
      </span>
      <p className='col-start-2 row-start-2 font-mono text-sm text-secondary-foreground lg:row-span-2 lg:row-start-1 lg:mb-3 lg:self-end'>
        <span aria-hidden='true'>{dateRange}</span>
        <span className='sr-only'>{dateRangeLabel}</span>
      </p>
      <div className='col-start-3 row-start-1 lg:row-span-2 lg:self-end'>
        <SkillActionsMenu onRemove={onRemove} skillName={skillName} surface='full' />
      </div>
    </motion.header>
  )
}
