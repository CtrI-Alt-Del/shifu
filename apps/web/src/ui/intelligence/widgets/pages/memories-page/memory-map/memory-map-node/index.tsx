import { Handle, type Node, type NodeProps, Position } from '@xyflow/react'

import { motion } from 'motion/react'

import { ENTRANCE_POP } from '@/constants/motion-variants'
import type { LearnerMemory } from '@/core/intelligence/learner-memory'
import { LEARNER_MEMORY_CATEGORY_PRESENTATION } from '@/ui/intelligence/constants/learner-memory-categories'
import { Icon } from '@/ui/shared/widgets/components/icon'

export type MemoryMapNodeData = {
  memory: LearnerMemory
  isSelected: boolean
  onSelect: (memoryId: string) => void
}
export type MemoryMapNodeType = Node<MemoryMapNodeData, 'memoryNode'>

export const MemoryMapNode = ({ data }: NodeProps<MemoryMapNodeType>) => {
  const { memory, isSelected, onSelect } = data
  const presentation = LEARNER_MEMORY_CATEGORY_PRESENTATION[memory.category]

  return (
    <div className='relative flex size-20 items-center justify-center'>
      <Handle
        className='pointer-events-none opacity-0'
        isConnectable={false}
        position={Position.Top}
        style={{ top: '50%' }}
        type='target'
      />
      <Handle
        className='pointer-events-none opacity-0'
        isConnectable={false}
        position={Position.Top}
        style={{ top: '50%' }}
        type='source'
      />
      <button
        aria-label={`${presentation.label}: ${memory.content}`}
        aria-pressed={isSelected}
        className='group nodrag nopan pointer-events-auto flex size-20 items-center justify-center rounded-full focus-visible:outline-none'
        onClick={() => onSelect(memory.id)}
        type='button'
      >
        {/* Only the circle pops: React Flow owns the node wrapper's transform. */}
        <motion.span
          variants={ENTRANCE_POP}
          className={`flex size-11 items-center justify-center rounded-full border-2 transition-colors group-focus-visible:outline-2 group-focus-visible:outline-offset-2 group-focus-visible:outline-selo-text ${isSelected ? 'border-primary! bg-primary/20 ring-4 ring-primary/30' : 'border-selo-text! bg-surface-alt ring-4 ring-selo-text/15 group-hover:bg-muted'}`}
        >
          <Icon name={presentation.icon} className='size-5 text-foreground' />
        </motion.span>
      </button>
      {isSelected ? (
        <span
          aria-hidden='true'
          className='pointer-events-none absolute top-full -mt-1 line-clamp-2 w-44 rounded bg-card px-1 text-center text-sm text-foreground'
        >
          {memory.content}
        </span>
      ) : null}
    </div>
  )
}
