import { cleanup, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ROUTES } from '@/constants/routes'
import type { MentorContextValue } from '@/ui/intelligence/contexts/mentor-context/types'
import { useMentorContext } from '@/ui/intelligence/hooks/use-mentor-context'
import { useMentorChat } from '../use-mentor-chat'

const mocks = vi.hoisted(() => ({
  navigate: vi.fn(),
  location: { pathname: '/gamification' },
}))
vi.mock('@tanstack/react-router', () => ({
  useLocation: () => mocks.location,
  useNavigate: () => mocks.navigate,
}))
vi.mock('@/ui/intelligence/hooks/use-mentor-context', () => ({
  useMentorContext: vi.fn(),
}))
const useMentorContextMock = vi.mocked(useMentorContext)

const baseValue: MentorContextValue = {
  selectedSessionId: null,
  sessionDetail: null,
  sessionsPage: { items: [], nextCursor: null },
  draft: '',
  search: '',
  isPanelOpen: false,
  panelView: 'conversation',
  activeDialog: null,
  dialogSessionId: null,
  isValidatingScope: false,
  isReadingHistory: false,
  isReadingMessages: false,
  isSubmittingFirstMessage: false,
  isRenamingSession: false,
  isRemovingSession: false,
  scopeError: null,
  historyError: null,
  conversationError: null,
  submissionError: null,
  renameError: null,
  removalError: null,
  openPanel: vi.fn(),
  closePanel: vi.fn(),
  showPanelHistory: vi.fn(),
  showPanelConversation: vi.fn(),
  expandConversation: vi.fn(),
  startNewConversation: vi.fn(),
  selectSession: vi.fn(),
  setDraft: vi.fn(),
  setSearch: vi.fn(),
  sendFirstMessage: vi.fn(),
  loadMoreSessions: vi.fn(),
  loadOlderMessages: vi.fn(),
  openRenameDialog: vi.fn(),
  openRemoveDialog: vi.fn(),
  closeDialog: vi.fn(),
  renameSession: vi.fn(),
  removeSession: vi.fn(),
  refresh: vi.fn(),
}

describe('useMentorChat', () => {
  afterEach(cleanup)

  it('delegates page selection for page-owned URL synchronization', async () => {
    mocks.navigate.mockReset()
    const selectSession = vi.fn().mockResolvedValue(undefined)
    useMentorContextMock.mockReturnValue({ ...baseValue, selectSession })
    const { result } = renderHook(() => useMentorChat('page'))
    await result.current.handleSelectSession('01J7T8AC91Z5K8M4JQ8C2D6F0B')
    expect(selectSession).toHaveBeenCalledWith('01J7T8AC91Z5K8M4JQ8C2D6F0B')
    expect(mocks.navigate).not.toHaveBeenCalled()
  })

  it('creates a draft without a session parameter and delegates new selection state', () => {
    useMentorContextMock.mockReturnValue(baseValue)
    const { result } = renderHook(() => useMentorChat('page'))
    result.current.handleStartNewConversation()
    expect(baseValue.startNewConversation).toHaveBeenCalledOnce()
    expect(mocks.navigate).not.toHaveBeenCalled()
  })

  it('keeps floating-panel session actions in the shared context without page navigation', async () => {
    mocks.navigate.mockReset()
    mocks.location.pathname = '/gamification'
    const selectSession = vi.fn().mockResolvedValue(undefined)
    const startNewConversation = vi.fn()
    useMentorContextMock.mockReturnValue({
      ...baseValue,
      selectSession,
      startNewConversation,
    })
    const { result } = renderHook(() => useMentorChat('fab'))
    await result.current.handleSelectSession('session-2')
    result.current.handleStartNewConversation()
    expect(selectSession).toHaveBeenCalledWith('session-2')
    expect(startNewConversation).toHaveBeenCalledOnce()
    expect(mocks.navigate).not.toHaveBeenCalled()
  })

  it('delegates a floating-panel draft on the page route without a second URL writer', () => {
    mocks.navigate.mockReset()
    mocks.location.pathname = ROUTES.intelligence
    const startNewConversation = vi.fn()
    useMentorContextMock.mockReturnValue({ ...baseValue, startNewConversation })
    const { result } = renderHook(() => useMentorChat('fab'))

    result.current.handleStartNewConversation()

    expect(startNewConversation).toHaveBeenCalledOnce()
    expect(mocks.navigate).not.toHaveBeenCalled()
  })
})
