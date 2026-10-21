import { MemoryChangeMarker } from './memory-change-marker'
import { MessageItem } from './message-list/message-item'
import { ResponseStatus } from './response-status'
import { SummaryMarker } from './summary-marker'
import { Button } from '@/ui/shadcn/button'
import { EmptyState } from './empty-state'
import { Composer } from './composer'
import { MessageList } from './message-list'
import { LoadingSkeleton } from './loading-skeleton'
import { useConversation } from './use-conversation'

export type ConversationProps = { surface?: 'page' | 'fab' }

export const Conversation = ({ surface = 'fab' }: ConversationProps) => {
  const {
    response,
    isCancellingResponse,
    isRetryingResponse,
    isSummarizingContext,
    cancelResponse,
    retryResponse,
    conversationError,
    handleScroll,
    isReadingMessages,
    isReadingOlderMessages,
    loadOlderMessages,
    refresh,
    scrollRef,
    selectedSessionId,
    sessionDetail,
    conversationItems,
    trailingMemoryItems,
  } = useConversation()
  const messages = sessionDetail?.messages.items ?? []

  return (
    <section aria-label='Conversa com o Mentor' className='flex min-h-0 flex-1 flex-col'>
      <div
        className={`flex min-h-0 flex-1 flex-col overflow-y-auto py-5 [scrollbar-color:var(--border)_transparent] [scrollbar-width:thin] ${surface === 'fab' ? 'px-6' : 'px-4'}`}
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
        {conversationItems.length ? (
          <MessageList items={conversationItems} surface={surface} />
        ) : !isReadingMessages && !conversationError ? (
          <EmptyState surface={surface} />
        ) : null}
        {response && response.blocks.length > 0 ? (
          <ol aria-label='Resposta do Mentor' className='mt-4'>
            <MessageItem
              surface={surface}
              response={response}
              message={{
                id: response.attemptId,
                sessionId: selectedSessionId ?? '',
                role: 'mentor',
                content: '',
                createdAt: '',
                inReplyToMessageId: response.learnerMessageId,
                attachments: [],
              }}
            />
          </ol>
        ) : null}
        {response && isSummarizingContext ? (
          <div className='space-y-2 py-3'>
            <SummaryMarker variant='processing' />
            <Button
              className='min-h-11'
              disabled={isCancellingResponse || isRetryingResponse}
              onClick={() => void cancelResponse()}
              variant='ghost'
            >
              Cancelar resposta
            </Button>
          </div>
        ) : response ? (
          <ResponseStatus
            response={response}
            isPending={isCancellingResponse || isRetryingResponse}
            onCancel={cancelResponse}
            onRetry={retryResponse}
          />
        ) : null}
        {trailingMemoryItems.length > 0 ? (
          <ul aria-label='Memórias desta resposta'>
            {trailingMemoryItems.map((item) => (
              <li key={item.id}>
                <MemoryChangeMarker item={item} />
              </li>
            ))}
          </ul>
        ) : null}
        {isReadingOlderMessages && messages.length > 0 ? (
          <p aria-live='polite' className='py-2 text-center text-sm'>
            Carregando mensagens anteriores…
          </p>
        ) : null}
      </div>
      <Composer surface={surface} />
    </section>
  )
}
