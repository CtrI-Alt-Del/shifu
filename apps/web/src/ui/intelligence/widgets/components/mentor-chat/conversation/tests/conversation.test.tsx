import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { MentorContextValue } from '@/ui/intelligence/contexts/mentor-context/types'
import { useMentorContext } from '@/ui/intelligence/hooks/use-mentor-context'
import { Conversation } from '..'
import type { MentorMessage } from '@/rest/services/intelligence-service'
import { useConversation } from '../use-conversation'

vi.mock('../use-conversation', () => ({ useConversation: vi.fn() }))
vi.mock('@/ui/intelligence/hooks/use-mentor-context', () => ({
  useMentorContext: vi.fn(),
}))
const useConversationMock = vi.mocked(useConversation)
const useMentorContextMock = vi.mocked(useMentorContext)

const mentorValue = {
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
} as unknown as MentorContextValue

describe('Conversation', () => {
  afterEach(cleanup)

  it('shows message skeletons until loading resolves without flashing the welcome state', () => {
    useMentorContextMock.mockReturnValue(mentorValue)
    const value = {
      ...mentorValue,
      isReadingMessages: true,
      handleScroll: vi.fn(),
      scrollRef: { current: null },
    }
    useConversationMock.mockReturnValue(value)
    const { container, rerender } = render(<Conversation surface='page' />)
    expect(screen.getByRole('status')).toHaveTextContent('Carregando conversa…')
    expect(container.querySelector('[data-slot="skeleton"]')).not.toBeNull()
    expect(screen.queryByRole('heading', { name: 'Como posso ajudar?' })).toBeNull()
    useConversationMock.mockReturnValue({ ...value, isReadingMessages: false })
    rerender(<Conversation surface='page' />)
    expect(screen.queryByRole('status')).toBeNull()
    expect(screen.getByRole('heading', { name: 'Como posso ajudar?' })).toBeVisible()
  })

  it('renders accepted messages, pending status and the unavailable subsequent-send state', () => {
    useMentorContextMock.mockReturnValue(mentorValue)
    useConversationMock.mockReturnValue({
      ...mentorValue,
      handleScroll: vi.fn(),
      refresh: vi.fn(),
      scrollRef: { current: null },
    })
    render(<Conversation />)
    expect(screen.getByRole('heading', { name: 'Como posso ajudar?' })).toBeVisible()
    expect(screen.getByLabelText('Escreva sua mensagem para o Mentor')).toBeEnabled()
    expect(
      screen.getByRole('button', {
        name: 'Anexar arquivo ou imagem. Indisponível no momento',
      }),
    ).toBeDisabled()
  })

  it('renders older-page, loading and recoverable conversation states', () => {
    useMentorContextMock.mockReturnValue(mentorValue)
    const messages: MentorMessage[] = [
      {
        id: 'learner-pending',
        sessionId: 'session-1',
        role: 'learner',
        content: 'Pergunta salva',
        inReplyToMessageId: null,
        createdAt: '2026-10-08T12:00:00Z',
      },
      {
        id: 'mentor-reply',
        sessionId: 'session-1',
        role: 'mentor',
        content: 'Resposta',
        inReplyToMessageId: 'learner-pending',
        createdAt: '2026-10-08T12:01:00Z',
      },
    ]
    const loadOlderMessages = vi.fn()
    const refresh = vi.fn()
    const conversationState = {
      ...mentorValue,
      conversationError: 'Falha temporária',
      handleScroll: vi.fn(),
      isReadingMessages: false,
      loadOlderMessages,
      refresh,
      scrollRef: { current: null },
      selectedSessionId: 'session-1',
      sessionDetail: {
        session: {
          id: 'session-1',
          title: 'Título',
          createdAt: '',
          updatedAt: '',
          lastActivityAt: '',
        },
        messages: { items: messages, nextCursor: 'older' },
        pendingLearnerMessageId: null,
      },
    } as unknown as ReturnType<typeof useConversation>
    useConversationMock.mockReturnValue(conversationState)
    const { rerender } = render(<Conversation />)
    expect(
      screen.getByText('Mensagem salva. A resposta ainda não está disponível.'),
    ).toBeVisible()
    expect(screen.getByText('Resposta')).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Carregar mensagens anteriores' }))
    expect(loadOlderMessages).toHaveBeenCalledOnce()
    useConversationMock.mockReturnValue({ ...conversationState, isReadingMessages: true })
    rerender(<Conversation />)
    expect(screen.getByText('Carregando mensagens anteriores…')).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    expect(refresh).toHaveBeenCalledOnce()
  })
})
