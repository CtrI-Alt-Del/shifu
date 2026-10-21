import { AnimatePresence } from 'motion/react'
import { MessageItem } from './message-item'
import { MemoryChangeMarker } from '../memory-change-marker'
import { SummaryMarker } from '../summary-marker'
import type { ConversationItem } from '../use-conversation'

export type MessageListProps = { items: ConversationItem[]; surface?: 'page' | 'fab' }

export const MessageList = ({ items, surface = 'page' }: MessageListProps) => (
  <ol aria-label='Mensagens da conversa' className='space-y-4'>
    <AnimatePresence initial={false}>
      {items.map((item) =>
        item.kind === 'message' ? (
          <MessageItem key={item.message.id} message={item.message} surface={surface} />
        ) : item.kind === 'summary-marker' ? (
          <li key={`summary-marker-${item.marker.version}`}>
            <SummaryMarker marker={item.marker} variant='ready' />
          </li>
        ) : item.kind === 'memory-change' ? (
          <li key={`memory-change-${item.item.id}`}>
            <MemoryChangeMarker item={item.item} />
          </li>
        ) : (
          <li key={`summary-failure-${item.messageId}`}>
            <SummaryMarker variant='failed' />
          </li>
        ),
      )}
    </AnimatePresence>
  </ol>
)
