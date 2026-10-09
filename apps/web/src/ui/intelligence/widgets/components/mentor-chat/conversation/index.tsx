import { Button } from '@/ui/shadcn/button'
import { EmptyState } from './empty-state'
import { Composer } from './composer'
import { MessageList } from './message-list'
import { LoadingSkeleton } from './loading-skeleton'
import { useConversation } from './use-conversation'

export type ConversationProps = { surface?: 'page' | 'fab' }

export const Conversation = ({ surface = 'fab' }: ConversationProps) => {
  const {
    conversationError,
    handleScroll,
    isReadingMessages,
    loadOlderMessages,
    refresh,
    scrollRef,
    selectedSessionId,
    sessionDetail,
  } = useConversation()
  const messages = sessionDetail?.messages.items ?? []

  return (
    <section aria-label='Conversa com o Mentor' className='flex min-h-0 flex-1 flex-col'>
      <div
        className={`flex min-h-0 flex-1 flex-col overflow-y-auto py-5 ${surface === 'fab' ? 'px-6' : 'px-4'}`}
        onScroll={handleScroll}
        ref={scrollRef}
      >
        {sessionDetail?.messages.nextCursor ? (
          <Button
            className='mb-4 border border-control-border'
            disabled={isReadingMessages}
            onClick={() => void loadOlderMessages()}
            variant='ghost'
          >
            Carregar mensagens anteriores
          </Button>
        ) : null}
        {isReadingMessages && messages.length === 0 ? <LoadingSkeleton /> : null}
        {conversationError ? (
          <div className='space-y-2' role='alert'>
            <p>{conversationError}</p>
            <Button onClick={() => selectedSessionId && void refresh()} variant='ghost'>
              Tentar novamente
            </Button>
          </div>
        ) : null}
        {messages.length ? (
          <MessageList messages={messages} surface={surface} />
        ) : !isReadingMessages && !conversationError ? (
          <EmptyState surface={surface} />
        ) : null}
        {isReadingMessages && messages.length > 0 ? (
          <p aria-live='polite' className='py-2 text-center text-sm'>
            Carregando mensagens anteriores…
          </p>
        ) : null}
      </div>
      <Composer surface={surface} />
    </section>
  )
}
