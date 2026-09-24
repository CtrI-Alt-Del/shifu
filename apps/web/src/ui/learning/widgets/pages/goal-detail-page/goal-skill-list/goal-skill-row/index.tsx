import { Link } from '@tanstack/react-router'

import type { GoalSkillDetail } from '@/core/learning/goal-detail'
import { SkillStatus } from '@/ui/learning/widgets/components/skill-status'
import { Icon } from '@/ui/shared/widgets/components/icon'
import { ProgressMeter } from '@/ui/shared/widgets/components/progress-meter'
import { Button } from '@/ui/shadcn/button'

export type GoalSkillRowProps = { goalId: string; skill: GoalSkillDetail }

export const GoalSkillRow = ({ goalId, skill }: GoalSkillRowProps) => (
  <li className='flex flex-col gap-4 rounded-lg border border-border bg-card p-4 sm:flex-row sm:items-center sm:justify-between'>
    <Link
      className='min-w-0 flex-1 rounded-md hover:text-primary'
      params={{ goalId, skillId: skill.skillExperienceId }}
      to='/learning/goals/$goalId/skills/$skillId'
    >
      <span className='block break-words font-semibold'>{skill.name}</span>
      {skill.inclusionReason ? (
        <span className='mt-1 block text-sm text-muted-foreground'>
          {skill.inclusionReason}
        </span>
      ) : null}
    </Link>
    <div className='flex flex-wrap items-center gap-4'>
      <SkillStatus status={skill.status} />
      {skill.status === 'learning' && skill.progress !== null ? (
        <div className='w-40'>
          <ProgressMeter
            label={`Progresso de ${skill.name}`}
            tone='success'
            value={skill.progress}
          />
        </div>
      ) : null}
      <div>
        <Button
          aria-describedby={`skill-actions-${skill.skillExperienceId}`}
          aria-label={`Mais ações de ${skill.name}`}
          className='px-3'
          disabled
          type='button'
          variant='ghost'
        >
          <Icon name='ellipsis' size={20} />
        </Button>
        <span className='sr-only' id={`skill-actions-${skill.skillExperienceId}`}>
          Disponível em uma próxima atualização
        </span>
      </div>
    </div>
  </li>
)
