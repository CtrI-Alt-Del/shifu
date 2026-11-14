import { motion } from 'motion/react'

import { ENTRANCE_SECTION, ENTRANCE_SLIDE } from '@/constants/motion-variants'
import { MotionEntrance } from '@/ui/shared/widgets/components/motion-entrance'

import { SessionHistory } from './session-history'
import { Conversation } from './conversation'
import { LoadingSkeleton } from './loading-skeleton'
import { MentorChatHeader } from './header'
import { RemoveSessionDialog } from './remove-session-dialog'
import { RenameSessionDialog } from './rename-session-dialog'
import { useMentorChat, type MentorChatSurface } from './use-mentor-chat'

export type MentorChatProps = { surface: MentorChatSurface }

export const MentorChat = ({ surface }: MentorChatProps) => {
  const mentor = useMentorChat(surface)
  const title = mentor.sessionDetail?.session.title ?? 'Nova conversa'
  const selectedSessionId = mentor.sessionDetail?.session.id

  return (
    <section
      className={`flex min-h-0 flex-col ${surface === 'page' ? 'h-[calc(100dvh-12rem)] lg:-mt-2 lg:mx-2 lg:h-[calc(100dvh-8rem)]' : 'h-full bg-surface-alt'}`}
    >
      {mentor.isValidatingScope ? (
        <LoadingSkeleton surface={surface} />
      ) : mentor.scopeError ? (
        <p
          className='m-4 rounded-xl border border-control-border p-4 text-sm'
          role='alert'
        >
          {mentor.scopeError}
        </p>
      ) : surface === 'page' ? (
        <MotionEntrance className='flex min-h-0 flex-1 gap-5'>
          <motion.aside
            className={`${mentor.panelView === 'history' ? 'flex w-full' : 'hidden'} h-full min-h-0 shrink-0 rounded-xl border border-border bg-surface-alt sm:flex sm:w-[300px]`}
            variants={ENTRANCE_SLIDE}
          >
            <SessionHistory
              onShowConversation={mentor.showPanelConversation}
              onNewConversation={mentor.handleStartNewConversation}
              onSelectSession={mentor.handleSelectSession}
              surface='page'
            />
          </motion.aside>
          <motion.div
            className={`${mentor.panelView === 'conversation' ? 'flex' : 'hidden'} min-h-0 min-w-0 flex-1 flex-col sm:flex`}
            variants={ENTRANCE_SECTION}
          >
            <MentorChatHeader
              isDraft={!selectedSessionId}
              isHistoryVisible={mentor.panelView === 'history'}
              onClose={mentor.closePanel}
              onExpand={mentor.expandConversation}
              onNewConversation={mentor.handleStartNewConversation}
              onRename={
                selectedSessionId
                  ? () => mentor.openRenameDialog(selectedSessionId)
                  : undefined
              }
              onShowConversation={mentor.showPanelConversation}
              onShowHistory={mentor.showPanelHistory}
              surface={surface}
              title={title}
            />
            <Conversation surface={surface} />
          </motion.div>
        </MotionEntrance>
      ) : (
        <>
          <MentorChatHeader
            isDraft={!selectedSessionId}
            isHistoryVisible={mentor.panelView === 'history'}
            onClose={mentor.closePanel}
            onExpand={mentor.expandConversation}
            onNewConversation={mentor.handleStartNewConversation}
            onShowConversation={mentor.showPanelConversation}
            onShowHistory={mentor.showPanelHistory}
            surface={surface}
            title={title}
          />
          <div className='flex min-h-0 flex-1'>
            {mentor.panelView === 'history' ? (
              <aside className='w-full'>
                <SessionHistory
                  onNewConversation={mentor.handleStartNewConversation}
                  onSelectSession={mentor.handleSelectSession}
                />
              </aside>
            ) : null}
            {mentor.panelView === 'conversation' ? (
              <div className='flex min-w-0 flex-1'>
                <Conversation surface={surface} />
              </div>
            ) : null}
          </div>
        </>
      )}
      <RenameSessionDialog />
      <RemoveSessionDialog />
    </section>
  )
}
