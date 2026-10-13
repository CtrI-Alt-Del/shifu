import type { MentorMessage } from '@/rest/services/intelligence-service'
import { AnimatePresence } from 'motion/react'
import { MessageItem } from './message-item'

export type MessageListProps = { messages: MentorMessage[]; surface?: 'page' | 'fab' }

export const MessageList = ({ messages, surface = 'page' }: MessageListProps) => (
  <ol aria-label='Mensagens da conversa' className='space-y-4'>
    <AnimatePresence initial={false}>
      {messages.map((message) => (
        <MessageItem key={message.id} message={message} surface={surface} />
      ))}
    </AnimatePresence>
  </ol>
)
