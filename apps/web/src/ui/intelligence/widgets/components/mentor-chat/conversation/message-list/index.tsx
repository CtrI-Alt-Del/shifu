import { AnimatePresence, MotionConfig, motion } from 'motion/react'

import { ENTRANCE_MESSAGE_LIST } from '@/constants/motion-variants'

import { MessageItem } from './message-item'
import { MemoryChangeMarker } from '../memory-change-marker'
import { SummaryMarker } from '../summary-marker'
import { SkillActionCard } from './skill-action-card'
import type { ConversationItem } from '../use-conversation'
import { useMessageList } from './use-message-list'

export type MessageListProps = { items: ConversationItem[]; surface?: 'page' | 'fab' }

export const MessageList = ({ items, surface = 'page' }: MessageListProps) => {
  const { initial } = useMessageList()

  return (
    <MotionConfig reducedMotion='user'>
      <motion.ol
        animate='visible'
        aria-label='Mensagens da conversa'
        className='space-y-4'
        initial={initial}
        variants={ENTRANCE_MESSAGE_LIST}
      >
        <AnimatePresence>
          {items.map((item) =>
            item.kind === 'message' ? (
              <MessageItem
                key={item.message.id}
                message={item.message}
                surface={surface}
              />
            ) : item.kind === 'summary-marker' ? (
              <li key={`summary-marker-${item.marker.version}`}>
                <SummaryMarker marker={item.marker} variant='ready' />
              </li>
            ) : item.kind === 'action' ? (
              <li key={`action-${item.proposal.id}`}>
                <SkillActionCard proposal={item.proposal} />
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
      </motion.ol>
    </MotionConfig>
  )
}
