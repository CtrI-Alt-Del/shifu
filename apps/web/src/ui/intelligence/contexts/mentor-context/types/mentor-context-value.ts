import type {
  MentorResponseSnapshot,
  SubmitMentorMessageInput,
} from '@/core/intelligence/mentor-response'
import type {
  MentorSessionDetail,
  MentorSessionsPage,
} from '@/rest/services/intelligence-service'
import type { MentorAttachment } from '@/core/intelligence/mentor-attachment'
import type { MentorSessionSummaryState } from '@/core/intelligence/mentor-session-summary'

import type {
  SpeechRecognitionStatus,
  SpeechLanguageAvailability,
  SpeechInstallationStatus,
} from '@/ui/shared/hooks/use-speech-recognition'

export type MentorDraftAttachment = {
  localKey: string
  uploadKey: string
  file: File
  previewUrl: string | null
  attachment: MentorAttachment | null
  error: string | null
  retryable?: boolean
}

export type MentorContextValue = {
  dictationStatus: SpeechRecognitionStatus
  dictationError: string | null
  dictationElapsedSeconds: number
  dictationLanguageAvailability: SpeechLanguageAvailability
  dictationInstallationStatus: SpeechInstallationStatus
  dictationInstallationError: string | null
  isDictationBusy: boolean
  canStartDictation: boolean
  canInstallDictationLanguage: boolean
  startDictation(surface?: 'page' | 'fab'): Promise<void>
  finishDictation(): void
  cancelDictation(): void
  installDictationLanguage(surface?: 'page' | 'fab'): Promise<void>
  releaseDictationSurface(surface: 'page' | 'fab'): void
  response: MentorResponseSnapshot | null
  isCancellingResponse: boolean
  isRetryingResponse: boolean
  submitMessage(input: SubmitMentorMessageInput): Promise<void>
  cancelResponse(): Promise<void>
  retryResponse(): Promise<void>
  shouldAnimateBlock(attemptId: string, blockKey: string): boolean
  markBlockPresented(attemptId: string, blockKey: string): void
  selectedSessionId: string | null
  sessionDetail: MentorSessionDetail | null
  summary: MentorSessionSummaryState
  isSummarizingContext: boolean
  sessionsPage: MentorSessionsPage
  draft: string
  draftAttachments: MentorDraftAttachment[]
  isPreparingAttachments: boolean
  search: string
  isPanelOpen: boolean
  panelView: 'conversation' | 'history'
  activeDialog: 'rename' | 'remove' | null
  dialogSessionId: string | null
  isValidatingScope: boolean
  isReadingHistory: boolean
  isReadingMessages: boolean
  isReadingOlderMessages: boolean
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
  addAttachments(files: File[]): Promise<void>
  retryAttachment(localKey: string): Promise<void>
  removeAttachment(localKey: string): Promise<void>
  setSearch(value: string): void
  sendFirstMessage(surface?: 'page' | 'fab'): Promise<void>
  loadMoreSessions(): Promise<void>
  loadOlderMessages(): Promise<void>
  revealMessage(messageId: string): Promise<boolean>
  openRenameDialog(sessionId: string): void
  openRemoveDialog(sessionId: string): void
  closeDialog(): void
  renameSession(title: string): Promise<void>
  removeSession(): Promise<void>
  refresh(): Promise<void>
}
