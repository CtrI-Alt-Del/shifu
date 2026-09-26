import { Link } from '@tanstack/react-router'

import type { GoalSkillDetail } from '@/core/learning/goal-detail'
import { SkillStatus } from '@/ui/learning/widgets/components/skill-status'
import { Icon } from '@/ui/shared/widgets/components/icon'
import { ProgressMeter } from '@/ui/shared/widgets/components/progress-meter'
import { SkillActionsMenu } from '@/ui/learning/widgets/components/skill-actions-menu'

export type GoalSkillRowProps = {
  goalId: string
  skill: GoalSkillDetail
  onRemove: (trigger: HTMLButtonElement) => void
}

export const GoalSkillRow = ({ goalId, skill, onRemove }: GoalSkillRowProps) => (
  <li className='flex min-h-16 flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center sm:gap-4'>
    <span
      className={`flex size-10 shrink-0 items-center justify-center rounded-md ${skill.status === 'learning' || skill.status === 'completed' ? 'bg-jade-tint text-success' : 'bg-muted text-muted-foreground'}`}
    >
      <Icon
        name={
          skill.status === 'diagnosing'
            ? 'search'
            : skill.status === 'not-started'
              ? 'circle-dashed'
              : 'circle'
        }
        size={18}
      />
    </span>
    <div className='min-w-0 flex-1'>
      <Link
        className='block break-words rounded-md font-semibold hover:text-primary'
        params={{ goalId, skillId: skill.skillId }}
        to='/learning/goals/$goalId/skills/$skillId'
      >
        {skill.name}
      </Link>
      {skill.inclusionReason ? (
        <span className='mt-1 block text-sm text-muted-foreground'>
          {skill.inclusionReason}
        </span>
      ) : null}
      {skill.status === 'learning' && skill.progress !== null ? (
        <div className='mt-3 max-w-80'>
          <ProgressMeter
            compact
            label={`Progresso de ${skill.name}`}
            tone='success'
            value={skill.progress}
          />
        </div>
      ) : null}
    </div>
    <div className='flex items-center gap-3 self-end sm:self-auto'>
      <span className='rounded-md bg-muted px-3 py-1'>
        <SkillStatus status={skill.status} />
      </span>
      <SkillActionsMenu onRemove={onRemove} skillName={skill.name} />
      <Icon className='text-muted-foreground' name='chevron-right' size={18} />
    </div>
  </li>
)
