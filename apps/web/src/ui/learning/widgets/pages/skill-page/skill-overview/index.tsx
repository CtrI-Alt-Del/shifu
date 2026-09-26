import {
  SKILL_STATUS_LABELS,
  type SkillExperienceStatus,
} from '@/core/learning/skill-experience'
import { Icon } from '@/ui/shared/widgets/components/icon'

export type SkillOverviewProps = {
  overallResult: number
  skillName: string
  skillStatus: SkillExperienceStatus
}

export const SkillOverview = ({
  overallResult,
  skillName,
  skillStatus,
}: SkillOverviewProps) => {
  return (
    <header className='flex items-start justify-between gap-3'>
      <div className='flex min-w-0 flex-col gap-3'>
        <h1 className='font-serif text-[40px] leading-[1.15] text-foreground'>
          {skillName}
        </h1>
        <div className='flex flex-wrap items-center gap-4'>
          <span className='inline-flex items-center gap-1.5 rounded-md bg-jade-tint px-2.5 py-[5px] text-xs font-semibold text-jade-text'>
            <Icon name='circle' size={12} />
            {SKILL_STATUS_LABELS[skillStatus]}
          </span>
          <span className='inline-flex items-center gap-2 rounded-md bg-surface-alt px-2 py-1'>
            <span className='text-[11px] font-medium text-secondary-foreground'>
              Resultado geral
            </span>
            <strong className='text-base font-bold tabular-nums text-jade-text'>
              {Math.round(overallResult)}%
            </strong>
          </span>
        </div>
      </div>
      <button
        aria-label='Ações da Habilidade'
        className='grid size-9 shrink-0 place-items-center rounded-md bg-muted text-muted-foreground transition-colors hover:text-foreground'
        type='button'
      >
        <Icon name='ellipsis' size={18} />
      </button>
    </header>
  )
}
