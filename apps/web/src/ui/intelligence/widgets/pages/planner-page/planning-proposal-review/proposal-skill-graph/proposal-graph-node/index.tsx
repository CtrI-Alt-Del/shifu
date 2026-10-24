import { Handle, Position, type Node, type NodeProps } from '@xyflow/react'

import type { PlanningProposalSkill } from '@/core/intelligence/planning-session'
import { Icon } from '@/ui/shared/widgets/components/icon'

export type ProposalGraphNodeType = Node<
  { skill: PlanningProposalSkill; width: number; height: number; isCompact: boolean },
  'proposalSkill'
>
export type ProposalRootNodeType = Node<
  { title: string; width: number; height: number },
  'proposalRoot'
>
export type ProposalFlowNodeType = ProposalGraphNodeType | ProposalRootNodeType

export const ProposalRootNode = ({ data }: NodeProps<ProposalRootNodeType>) => (
  <article
    aria-label={`Proposta de Objetivo: ${data.title}`}
    className='flex items-center gap-3 rounded-[10px] border border-selo-text bg-accent px-4 py-3.5'
    style={{ width: data.width }}
  >
    <span className='grid size-10 shrink-0 place-items-center rounded-md bg-primary text-primary-foreground'>
      <Icon name='target' size={18} />
    </span>
    <div className='flex min-w-0 flex-col gap-1'>
      <p className='break-words text-[15px] font-semibold leading-[1.25] text-foreground'>
        {data.title}
      </p>
      <p className='text-xs font-semibold text-selo-text'>Proposta de Objetivo</p>
    </div>
    <Handle className='opacity-0' position={Position.Bottom} type='source' />
  </article>
)

export const ProposalGraphNode = ({ data }: NodeProps<ProposalGraphNodeType>) => {
  const { skill, isCompact } = data

  return (
    <article
      aria-label={`Habilidade ${skill.name}`}
      className='flex flex-col gap-3 rounded-[10px] border border-border bg-surface-alt px-4 py-3 transition-colors focus-within:border-control-border hover:border-control-border'
      style={{ width: data.width }}
    >
      <Handle className='opacity-0' position={Position.Top} type='target' />
      <div className={isCompact ? 'flex flex-col gap-2' : 'flex items-center gap-3'}>
        <span className='grid size-[34px] shrink-0 place-items-center rounded-md bg-jade-tint text-jade-text'>
          <Icon name='graduation-cap' size={16} />
        </span>
        <p className='min-w-0 break-words text-sm font-semibold leading-[1.25] text-foreground'>
          {skill.name}
        </p>
      </div>
      <p className='text-[13px] leading-[1.5] text-secondary-foreground'>
        {skill.justification}
      </p>
      <Handle className='opacity-0' position={Position.Bottom} type='source' />
    </article>
  )
}
