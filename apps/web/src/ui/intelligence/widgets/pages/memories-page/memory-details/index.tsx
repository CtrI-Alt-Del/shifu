import type { LearnerMemory } from '@/core/intelligence/learner-memory'
import { LEARNER_MEMORY_CATEGORY_PRESENTATION } from '@/ui/intelligence/constants/learner-memory-categories'
import { Button } from '@/ui/shadcn/button'
import { useFormatInstant } from '@/ui/shared/hooks/use-format-instant'
import { Icon } from '@/ui/shared/widgets/components/icon'

import { MemoryOriginList } from './memory-origin-list'

export type MemoryDetailsProps = {
  memory: LearnerMemory
  onClose: () => void
  onEdit: () => void
  onDelete: () => void
}

const SECTION_LABEL_CLASS_NAME =
  'font-mono text-[11px] uppercase tracking-wider text-muted-foreground'

export const MemoryDetails = ({
  memory,
  onClose,
  onEdit,
  onDelete,
}: MemoryDetailsProps) => {
  const { formatShortDate, formatDateTime } = useFormatInstant()

  return (
    <section
      aria-label='Detalhes da memória'
      className='space-y-5 rounded-[10px] border border-border bg-card p-5'
    >
      <div className='flex items-start justify-between gap-3'>
        <p className='font-mono text-xs uppercase tracking-wider text-selo-text'>
          {LEARNER_MEMORY_CATEGORY_PRESENTATION[memory.category].detailLabel}
        </p>
        <Button
          aria-label='Fechar detalhes da memória'
          className='size-11 shrink-0 p-0!'
          onClick={onClose}
          type='button'
          variant='ghost'
        >
          <Icon name='x' className='size-4' />
        </Button>
      </div>
      <h2 className='break-words font-serif text-2xl font-normal leading-tight'>
        {memory.content}
      </h2>
      <div className='space-y-1 border-b border-border pb-4 text-xs text-muted-foreground'>
        <p>Declarada por você · criada em {formatShortDate(memory.createdAt)}</p>
        <p>Atualizada em {formatDateTime(memory.updatedAt)}</p>
      </div>
      <div className='space-y-2'>
        <h3 className={SECTION_LABEL_CLASS_NAME}>O que o Mentor lembra</h3>
        <p className='break-words rounded-md border border-border bg-muted p-4 text-sm'>
          {memory.content}
        </p>
      </div>
      <div className='space-y-2'>
        <h3 className={SECTION_LABEL_CLASS_NAME}>Origem</h3>
        <MemoryOriginList origins={memory.origins} />
      </div>
      {memory.concepts.length > 0 ? (
        <div className='space-y-2'>
          <h3 className={SECTION_LABEL_CLASS_NAME}>Relacionada a</h3>
          <ul aria-label='Conceitos relacionados' className='flex flex-wrap gap-2'>
            {memory.concepts.map((concept) => (
              <li
                className='rounded-md border border-jade-solid px-3 py-1 text-xs text-jade-text'
                key={concept.key}
              >
                {concept.label}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <p className='text-xs text-muted-foreground'>
        Esta memória orienta explicações; não altera sua proficiência.
      </p>
      <div className='flex flex-wrap gap-2'>
        <Button
          className='gap-2 border border-control-border text-foreground'
          onClick={onEdit}
          type='button'
          variant='ghost'
        >
          <Icon name='pencil' className='size-4' />
          Editar
        </Button>
        <Button
          className='gap-2 border border-selo-text text-selo-text'
          onClick={onDelete}
          type='button'
          variant='ghost'
        >
          <Icon name='trash-2' className='size-4' />
          Excluir
        </Button>
      </div>
    </section>
  )
}
