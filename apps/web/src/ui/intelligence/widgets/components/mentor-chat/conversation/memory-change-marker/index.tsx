import type { MentorConversationMemoryItem } from '@/core/intelligence/learner-memory'
import { LEARNER_MEMORY_CATEGORY_PRESENTATION } from '@/ui/intelligence/constants/learner-memory-categories'
import { Anchor } from '@/ui/shared/widgets/components/anchor'
import { Icon } from '@/ui/shared/widgets/components/icon'

export type MemoryChangeMarkerProps = {
  item: MentorConversationMemoryItem
}

export const MemoryChangeMarker = ({ item }: MemoryChangeMarkerProps) => {
  const isRemoved = item.memoryId === null
  const categoryLabel = LEARNER_MEMORY_CATEGORY_PRESENTATION[item.category].label
  const title = isRemoved
    ? 'Memória excluída'
    : item.kind === 'created'
      ? 'Memória criada'
      : 'Memória atualizada'

  return (
    <div className='space-y-1 px-1 py-2 font-sans text-[13px]'>
      <div className='flex min-h-11 flex-wrap items-center gap-x-2 gap-y-1'>
        <Icon className='size-4 shrink-0 text-muted-foreground' name='brain' />
        <span className='text-secondary-foreground'>{title}</span>
        {isRemoved ? null : (
          <Anchor
            className='inline-flex min-h-11 items-center rounded-md px-2 font-medium text-foreground hover:bg-white/5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-selo-text'
            route='intelligenceMemories'
            search={{ memory: item.memoryId ?? undefined }}
          >
            Ver memória
          </Anchor>
        )}
      </div>
      {isRemoved ? null : item.kind === 'created' ? (
        <p className='break-words text-muted-foreground'>
          {categoryLabel}: {item.content}
        </p>
      ) : (
        <>
          <p className='break-words text-muted-foreground'>
            Antes: {item.previousContent}
          </p>
          <p className='break-words text-muted-foreground'>Agora: {item.content}</p>
        </>
      )}
    </div>
  )
}
