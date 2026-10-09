import { useId } from 'react'

import { Button } from '@/ui/shadcn/button'
import { Input } from '@/ui/shadcn/input'
import { Skeleton } from '@/ui/shadcn/skeleton'
import { Icon } from '@/ui/shared/widgets/components/icon'
import { SessionItem } from './session-item'
import { useSessionHistory } from './use-session-history'

export type SessionHistoryProps = {
  surface?: 'page' | 'fab'
  onShowConversation?: () => void
  onNewConversation?: () => void
  onSelectSession?: (sessionId: string) => Promise<void>
}

export const SessionHistory = ({
  surface = 'fab',
  onShowConversation,
  onNewConversation,
  onSelectSession,
}: SessionHistoryProps) => {
  const searchId = useId()
  const {
    historyError,
    isReadingHistory,
    loadMoreSessions,
    listRef,
    loadSentinelRef,
    openRemoveDialog,
    openRenameDialog,
    search,
    refresh,
    startNewConversation,
    selectSession,
    selectedSessionId,
    sessionsPage,
    setSearch,
  } = useSessionHistory()

  return (
    <section
      aria-label='Histórico de conversas'
      className={`flex h-full min-h-0 w-full min-w-0 flex-col gap-2.5 ${surface === 'page' ? 'p-3' : 'p-6'}`}
    >
      {surface === 'page' ? (
        <div className='space-y-2.5'>
          <div className='flex items-center justify-between gap-2'>
            <h2 className='font-serif text-2xl'>Conversas</h2>
            {onShowConversation ? (
              <Button
                aria-label='Voltar à conversa'
                className='px-3 sm:hidden'
                onClick={onShowConversation}
                variant='ghost'
              >
                <Icon name='arrow-right' className='size-5' />
              </Button>
            ) : null}
          </div>
          <Button
            className='w-full gap-2'
            onClick={onNewConversation ?? startNewConversation}
          >
            <Icon name='plus' className='size-4' />
            Nova conversa
          </Button>
        </div>
      ) : (
        <Button
          className='w-full gap-2'
          onClick={onNewConversation ?? startNewConversation}
        >
          <Icon name='plus' className='size-4' />
          Nova conversa
        </Button>
      )}
      <label className='sr-only' htmlFor={searchId}>
        Buscar conversa por título
      </label>
      <div className='relative'>
        <Icon
          name='search'
          className='pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground'
        />
        <Input
          className='pl-9'
          id={searchId}
          onChange={(event) => setSearch(event.currentTarget.value)}
          placeholder='Buscar conversas'
          type='search'
          value={search}
        />
      </div>
      {historyError ? (
        <div
          className='space-y-2 rounded-xl border border-control-border p-4'
          role='alert'
        >
          <p>{historyError}</p>
          <Button
            className='border border-control-border'
            onClick={() => void refresh()}
            variant='ghost'
          >
            Tentar novamente
          </Button>
        </div>
      ) : null}
      {!sessionsPage.items.length && !isReadingHistory ? (
        <p className='rounded-md border border-control-border bg-card p-3 text-sm text-muted-foreground'>
          Suas conversas aceitas aparecerão aqui.
        </p>
      ) : null}
      <ul className='min-h-0 flex-1 space-y-2 overflow-y-auto' ref={listRef}>
        {sessionsPage.items.map((session) => (
          <SessionItem
            isSelected={session.id === selectedSessionId}
            key={session.id}
            onRemove={() => openRemoveDialog(session.id)}
            onRename={() => openRenameDialog(session.id)}
            onSelect={() => void (onSelectSession ?? selectSession)(session.id)}
            session={session}
          />
        ))}
        {isReadingHistory ? (
          <li>
            <output className='sr-only'>Carregando histórico…</output>
            <div aria-hidden='true' className='space-y-2'>
              {['w-4/5', 'w-3/5', 'w-2/3'].map((titleWidth) => (
                <div
                  className='flex items-center gap-2 rounded-md border border-border bg-muted p-2'
                  key={titleWidth}
                >
                  <div className='flex min-h-11 min-w-0 flex-1 flex-col justify-center gap-2 px-1'>
                    <Skeleton className={`h-4 bg-border! ${titleWidth}`} />
                    <Skeleton className='h-3 w-12 bg-border!' />
                  </div>
                  <Skeleton className='size-5 shrink-0 bg-border!' />
                  <Skeleton className='size-5 shrink-0 bg-border!' />
                </div>
              ))}
            </div>
          </li>
        ) : null}
        <li ref={loadSentinelRef} aria-hidden='true' className='h-px' />
      </ul>
      {sessionsPage.nextCursor ? (
        <Button
          className='border border-control-border'
          disabled={isReadingHistory}
          onClick={() => void loadMoreSessions()}
          variant='ghost'
        >
          Carregar mais conversas
        </Button>
      ) : null}
    </section>
  )
}
