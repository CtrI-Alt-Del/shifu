import type { MentorSession } from '@/rest/services/intelligence-service'
import { Button } from '@/ui/shadcn/button'
import { Icon } from '@/ui/shared/widgets/components/icon'

export type SessionItemProps = {
  session: MentorSession
  isSelected: boolean
  onSelect: () => void
  onRename: () => void
  onRemove: () => void
}

export const SessionItem = ({
  session,
  isSelected,
  onSelect,
  onRename,
  onRemove,
}: SessionItemProps) => (
  <li
    className={`rounded-md border p-2 ${isSelected ? 'border-primary bg-accent' : 'border-border bg-muted'}`}
  >
    <div className='flex min-w-0 items-center gap-1'>
      <Button
        aria-current={isSelected ? 'page' : undefined}
        aria-label={`${session.title}${isSelected ? ' , conversa selecionada' : ''}`}
        title={session.title}
        className='min-h-11 min-w-0 flex-1 flex-col items-start! justify-center gap-1 whitespace-normal px-1! text-left'
        onClick={onSelect}
        variant='ghost'
      >
        <span className='line-clamp-2 w-full break-words text-sm font-semibold text-foreground'>
          {session.title}
        </span>
        <time
          className='text-xs font-normal text-muted-foreground'
          dateTime={session.lastActivityAt}
        >
          {new Intl.DateTimeFormat('pt-BR', { day: 'numeric', month: 'short' }).format(
            new Date(session.lastActivityAt),
          )}
        </time>
        {isSelected ? <span className='sr-only'>, conversa selecionada</span> : null}
      </Button>
      <div className='flex shrink-0 items-center'>
        <Button
          aria-label={`Renomear ${session.title}`}
          title='Renomear conversa'
          className='size-11 shrink-0 p-0!'
          onClick={onRename}
          variant='ghost'
        >
          <Icon name='pencil' className='size-3' />
        </Button>
        <Button
          aria-label={`Excluir ${session.title}`}
          title='Excluir conversa'
          className='size-11 shrink-0 p-0!'
          onClick={onRemove}
          variant='ghost'
        >
          <Icon name='trash-2' className='size-3' />
        </Button>
      </div>
    </div>
  </li>
)
