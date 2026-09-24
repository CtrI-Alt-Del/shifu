import { Handle, Position, type Node, type NodeProps } from '@xyflow/react'
import { Link } from '@tanstack/react-router'

import type { GoalSkillDetail } from '@/core/learning/goal-detail'
import { SkillStatus } from '@/ui/learning/widgets/components/skill-status'
import { Icon } from '@/ui/shared/widgets/components/icon'
import { ProgressMeter } from '@/ui/shared/widgets/components/progress-meter'
import { Button } from '@/ui/shadcn/button'

export type GoalGraphNodeData = { goalId: string; skill: GoalSkillDetail }
export type GoalGraphNodeType = Node<GoalGraphNodeData, 'goalSkill'>

export const GoalGraphNode = ({ data }: NodeProps<GoalGraphNodeType>) => {
  const { goalId, skill } = data
  return (
    <article className='w-64 rounded-lg border border-control-border bg-card p-4'>
      <Handle position={Position.Top} type='target' />
      <div className='flex items-start justify-between gap-3'>
        <Link
          aria-label={`Abrir Habilidade ${skill.name}`}
          className='min-w-0 break-words font-semibold hover:text-primary'
          params={{ goalId, skillId: skill.skillExperienceId }}
          to='/learning/goals/$goalId/skills/$skillId'
        >
          {skill.name}
        </Link>
        <Button
          aria-describedby={`graph-skill-actions-${skill.skillExperienceId}`}
          aria-label={`Mais ações de ${skill.name}`}
          className='size-11 shrink-0 px-0'
          disabled
          type='button'
          variant='ghost'
        >
          <Icon name='ellipsis' size={18} />
        </Button>
        <span className='sr-only' id={`graph-skill-actions-${skill.skillExperienceId}`}>
          Disponível em uma próxima atualização
        </span>
      </div>
      <div className='mt-3'>
        <SkillStatus status={skill.status} />
      </div>
      {skill.status === 'learning' && skill.progress !== null ? (
        <div className='mt-3'>
          <ProgressMeter
            label={`Progresso de ${skill.name}`}
            tone='success'
            value={skill.progress}
          />
        </div>
      ) : null}
      <Handle position={Position.Bottom} type='source' />
    </article>
  )
}
