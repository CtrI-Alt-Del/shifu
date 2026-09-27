import { Handle, Position, type Node, type NodeProps } from '@xyflow/react'
import { Link } from '@tanstack/react-router'

import type { GoalSkillDetail } from '@/core/learning/goal-detail'
import { SkillStatus } from '@/ui/learning/widgets/components/skill-status'
import { Icon } from '@/ui/shared/widgets/components/icon'
import { ProgressMeter } from '@/ui/shared/widgets/components/progress-meter'
import { SkillActionsMenu } from '@/ui/learning/widgets/components/skill-actions-menu'

export type GoalGraphNodeData = {
  goalId: string
  skill: GoalSkillDetail
  onRemove: (trigger: HTMLButtonElement) => void
}
export type GoalGraphNodeType = Node<GoalGraphNodeData, 'goalSkill'>
export type GoalRootNodeType = Node<{ title: string }, 'goalRoot'>
export type GoalFlowNodeType = GoalGraphNodeType | GoalRootNodeType

export const GoalRootNode = ({ data }: NodeProps<GoalRootNodeType>) => (
  <article className='flex w-[388px] items-center gap-3 rounded-[10px] border border-selo-text bg-accent p-4'>
    <span className='flex size-10 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground'>
      <Icon name='target' size={18} />
    </span>
    <div className='min-w-0'>
      <p className='break-words text-[15px] font-semibold leading-tight'>{data.title}</p>
      <p className='mt-1 text-xs font-semibold text-selo-text'>Objetivo</p>
    </div>
    <Handle className='opacity-0' position={Position.Bottom} type='source' />
  </article>
)

export const GoalGraphNode = ({ data }: NodeProps<GoalGraphNodeType>) => {
  const { goalId, skill, onRemove } = data
  return (
    <article className='w-88 rounded-[10px] border border-border bg-surface-alt p-4 transition-colors hover:border-control-border focus-within:border-control-border'>
      <Handle className='opacity-0' position={Position.Top} type='target' />
      <div className='flex items-start justify-between gap-3'>
        <span
          className={`flex size-[34px] shrink-0 items-center justify-center rounded-md ${skill.status === 'learning' || skill.status === 'completed' ? 'bg-jade-tint text-success' : 'bg-muted text-muted-foreground'}`}
        >
          <Icon
            name={
              skill.status === 'diagnosing'
                ? 'search'
                : skill.status === 'not-started'
                  ? 'circle-dashed'
                  : 'circle'
            }
            size={16}
          />
        </span>
        <Link
          aria-label={`Abrir Habilidade ${skill.name}`}
          className='min-w-0 flex-1 break-words text-sm font-semibold leading-tight hover:text-primary'
          params={{ goalId, skillId: skill.skillId }}
          to='/learning/goals/$goalId/skills/$skillId'
        >
          {skill.name}
        </Link>
        <SkillActionsMenu onRemove={onRemove} skillName={skill.name} />
      </div>
      {skill.status === 'learning' && skill.progress !== null ? (
        <div className='mt-3'>
          <ProgressMeter
            compact
            label={`Progresso de ${skill.name}`}
            tone='success'
            value={skill.progress}
          />
        </div>
      ) : null}
      <div className='mt-3'>
        <SkillStatus status={skill.status} />
      </div>
      <Handle className='opacity-0' position={Position.Bottom} type='source' />
    </article>
  )
}
