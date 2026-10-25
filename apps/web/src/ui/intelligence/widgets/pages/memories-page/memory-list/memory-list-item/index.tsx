import { motion } from 'motion/react'

import { ENTRANCE_ROW } from '@/constants/motion-variants'
import type { LearnerMemory } from '@/core/intelligence/learner-memory'
import { LEARNER_MEMORY_CATEGORY_PRESENTATION } from '@/ui/intelligence/constants/learner-memory-categories'
import { useFormatInstant } from '@/ui/shared/hooks/use-format-instant'

export type MemoryListItemProps = {
  memory: LearnerMemory
  isSelected: boolean
  onSelect: (memoryId: string) => void
}

export const MemoryListItem = ({ memory, isSelected, onSelect }: MemoryListItemProps) => {
  const { formatShortDate } = useFormatInstant()
  const isUpdated = memory.updatedAt !== memory.createdAt
  const provenance = isUpdated
    ? `Declarada por você · atualizada em ${formatShortDate(memory.updatedAt)}`
    : `Declarada por você · ${formatShortDate(memory.createdAt)}`

  return (
    <motion.li variants={ENTRANCE_ROW}>
      <button
        aria-pressed={isSelected}
        className={`flex min-h-11 w-full flex-col items-start gap-1 rounded-[10px] border px-4 py-3 text-left transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-selo-text ${isSelected ? 'border-jade-solid bg-jade-tint' : 'border-border bg-card hover:border-control-border'}`}
        onClick={() => onSelect(memory.id)}
        type='button'
      >
        <span className='text-xs text-muted-foreground'>
          {LEARNER_MEMORY_CATEGORY_PRESENTATION[memory.category].label}
        </span>
        <span className='break-words text-[15px] font-medium text-foreground'>
          {memory.content}
        </span>
        <span className='text-xs text-muted-foreground'>{provenance}</span>
      </button>
    </motion.li>
  )
}
