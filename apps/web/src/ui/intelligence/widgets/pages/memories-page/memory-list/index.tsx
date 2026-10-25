import { motion } from 'motion/react'

import { ENTRANCE_STAGGER } from '@/constants/motion-variants'
import type { LearnerMemory } from '@/core/intelligence/learner-memory'

import { MemoryListItem } from './memory-list-item'

export type MemoryListProps = {
  memories: LearnerMemory[]
  selectedMemoryId: string | null
  onSelectMemory: (memoryId: string) => void
}

export const MemoryList = ({
  memories,
  selectedMemoryId,
  onSelectMemory,
}: MemoryListProps) => (
  <motion.ul
    aria-label='Lista de memórias'
    className='space-y-2'
    variants={ENTRANCE_STAGGER}
  >
    {memories.map((memory) => (
      <MemoryListItem
        isSelected={memory.id === selectedMemoryId}
        key={memory.id}
        memory={memory}
        onSelect={onSelectMemory}
      />
    ))}
  </motion.ul>
)
