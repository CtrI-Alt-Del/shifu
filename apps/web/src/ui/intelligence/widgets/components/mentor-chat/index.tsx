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
      className={`flex min-h-0 flex-col ${surface === 'page' ? 'min-h-[calc(100vh-12rem)] lg:-mt-2 lg:mx-2 lg:min-h-[calc(100vh-7rem)]' : 'h-full bg-surface-alt'}`}
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
        <div className='flex min-h-0 flex-1 gap-5'>
          <aside
            className={`${mentor.panelView === 'history' ? 'flex w-full' : 'hidden'} min-h-0 shrink-0 rounded-xl border border-border bg-surface-alt sm:flex sm:w-[300px]`}
          >
            <SessionHistory
              onShowConversation={mentor.showPanelConversation}
              onNewConversation={mentor.handleStartNewConversation}
              onSelectSession={mentor.handleSelectSession}
              surface='page'
            />
          </aside>
          <div
            className={`${mentor.panelView === 'conversation' ? 'flex' : 'hidden'} min-w-0 flex-1 flex-col sm:flex`}
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
          </div>
        </div>
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
