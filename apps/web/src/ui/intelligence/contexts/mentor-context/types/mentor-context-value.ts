import type {
  MentorSessionDetail,
  MentorSessionsPage,
} from '@/rest/services/intelligence-service'

export type MentorContextValue = {
  selectedSessionId: string | null
  sessionDetail: MentorSessionDetail | null
  sessionsPage: MentorSessionsPage
  draft: string
  search: string
  isPanelOpen: boolean
  panelView: 'conversation' | 'history'
  activeDialog: 'rename' | 'remove' | null
  dialogSessionId: string | null
  isValidatingScope: boolean
  isReadingHistory: boolean
  isReadingMessages: boolean
  isSubmittingFirstMessage: boolean
  isRenamingSession: boolean
  isRemovingSession: boolean
  scopeError: string | null
  historyError: string | null
  conversationError: string | null
  submissionError: string | null
  renameError: string | null
  removalError: string | null
  openPanel(): void
  closePanel(): void
  showPanelHistory(): void
  showPanelConversation(): void
  expandConversation(): void
  startNewConversation(): void
  selectSession(sessionId: string): Promise<void>
  setDraft(value: string): void
  setSearch(value: string): void
  sendFirstMessage(): Promise<void>
  loadMoreSessions(): Promise<void>
  loadOlderMessages(): Promise<void>
  openRenameDialog(sessionId: string): void
  openRemoveDialog(sessionId: string): void
  closeDialog(): void
  renameSession(title: string): Promise<void>
  removeSession(): Promise<void>
  refresh(): Promise<void>
}
