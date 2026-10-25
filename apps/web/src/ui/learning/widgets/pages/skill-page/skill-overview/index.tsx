import { motion } from 'motion/react'

import {
  SKILL_STATUS_LABELS,
  type SkillExperienceStatus,
} from '@/core/learning/skill-experience'
import { ENTRANCE_SECTION } from '@/constants/motion-variants'
import { AnimatedNumber } from '@/ui/shared/widgets/components/animated-number'
import { Icon } from '@/ui/shared/widgets/components/icon'
import { SkillActionsMenu } from '@/ui/learning/widgets/components/skill-actions-menu'

export type SkillOverviewProps = {
  overallResult: number | null
  overallCoverageComplete: boolean
  skillName: string
  skillStatus: SkillExperienceStatus
  onRemove: () => void
}

export const SkillOverview = ({
  overallResult,
  skillName,
  skillStatus,
  onRemove,
}: SkillOverviewProps) => {
  return (
    <motion.header
      className='flex items-start justify-between gap-3'
      variants={ENTRANCE_SECTION}
    >
      <div className='flex min-w-0 flex-col gap-3'>
        <h1 className='font-serif text-[40px] leading-[1.15] text-foreground'>
          {skillName}
        </h1>
        <div className='flex flex-wrap items-center gap-4'>
          <span className='inline-flex items-center gap-1.5 rounded-md bg-jade-tint px-2.5 py-[5px] text-base font-semibold text-jade-text'>
            <Icon name='circle' size={14} />
            {SKILL_STATUS_LABELS[skillStatus]}
          </span>
          <span className='inline-flex items-center gap-2 rounded-md bg-surface-alt px-2 py-1'>
            <span className='text-sm font-medium text-secondary-foreground'>
              Progresso demonstrado
            </span>
            <strong className='text-lg font-bold tabular-nums text-jade-text'>
              {overallResult === null ? (
                'Sem evidência'
              ) : (
                <AnimatedNumber
                  delay={0.3}
                  format={(value) => `${value}%`}
                  value={Math.round(overallResult)}
                />
              )}
            </strong>
          </span>
        </div>
      </div>
      <SkillActionsMenu onRemove={onRemove} skillName={skillName} />
    </motion.header>
  )
}
