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
  <ul aria-label='Lista de memórias' className='space-y-2'>
    {memories.map((memory) => (
      <MemoryListItem
        isSelected={memory.id === selectedMemoryId}
        key={memory.id}
        memory={memory}
        onSelect={onSelectMemory}
      />
    ))}
  </ul>
)
