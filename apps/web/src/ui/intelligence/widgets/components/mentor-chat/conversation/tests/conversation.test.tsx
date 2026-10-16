import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { MentorContextValue } from '@/ui/intelligence/contexts/mentor-context/types'
import type { MentorResponseSnapshot } from '@/core/intelligence/mentor-response'
import { useMentorContext } from '@/ui/intelligence/hooks/use-mentor-context'
import { Conversation } from '..'
import type { MentorMessage } from '@/rest/services/intelligence-service'
import { useConversation } from '../use-conversation'

vi.mock('../use-conversation', () => ({ useConversation: vi.fn() }))
vi.mock('@/ui/intelligence/hooks/use-mentor-context', () => ({
  useMentorContext: vi.fn(),
}))
vi.mock('@/ui/intelligence/hooks/use-mentor-attachment-file-query', () => {
  const emptyAttachmentQuery = {
    mentorAttachmentFiles: {},
    mentorAttachmentFileErrors: {},
    mentorAttachmentFilesError: undefined,
    isReadingMentorAttachmentFiles: false,
  }
  return { useMentorAttachmentFileQuery: () => emptyAttachmentQuery }
})
const useConversationMock = vi.mocked(useConversation)
const useMentorContextMock = vi.mocked(useMentorContext)
const mockConversationValue = (value: object) =>
  useConversationMock.mockReturnValue({
    visibleMessages: undefined,
    ...value,
  } as unknown as ReturnType<typeof useConversation>)

const mentorValue = {
  selectedSessionId: null,
  sessionDetail: null,
  sessionsPage: { items: [], nextCursor: null },
  draft: '',
  draftAttachments: [],
  isPreparingAttachments: false,
  search: '',
  isPanelOpen: false,
  panelView: 'conversation',
  activeDialog: null,
  dialogSessionId: null,
  isValidatingScope: false,
  isReadingHistory: false,
  isReadingMessages: false,
  isReadingOlderMessages: false,
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
  addAttachments: vi.fn(),
  removeAttachment: vi.fn(),
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
    mockConversationValue(value)
    const { container, rerender } = render(<Conversation surface='page' />)
    expect(screen.getByRole('status')).toHaveTextContent('Carregando conversa…')
    expect(container.querySelector('[data-slot="skeleton"]')).not.toBeNull()
    expect(screen.queryByRole('heading', { name: 'Como posso ajudar?' })).toBeNull()
    mockConversationValue({ ...value, isReadingMessages: false })
    rerender(<Conversation surface='page' />)
    expect(screen.queryByRole('status')).toBeNull()
    expect(screen.getByRole('heading', { name: 'Como posso ajudar?' })).toBeVisible()
  })

  it('renders accepted messages, pending status and the unavailable subsequent-send state', () => {
    useMentorContextMock.mockReturnValue(mentorValue)
    mockConversationValue({
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
        name: 'Anexar arquivo ou imagem',
      }),
    ).toBeEnabled()
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
        attachments: [],
      },
      {
        id: 'mentor-reply',
        sessionId: 'session-1',
        role: 'mentor',
        content: 'Resposta',
        inReplyToMessageId: 'learner-pending',
        createdAt: '2026-10-08T12:01:00Z',
        attachments: [],
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
    mockConversationValue(conversationState)
    const { rerender } = render(<Conversation />)
    expect(screen.getByText('Pergunta salva')).toBeVisible()
    expect(screen.getByText('Resposta')).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Carregar mensagens anteriores' }))
    expect(loadOlderMessages).toHaveBeenCalledOnce()
    mockConversationValue({ ...conversationState, isReadingMessages: true })
    rerender(<Conversation />)
    expect(screen.queryByText('Carregando mensagens anteriores…')).toBeNull()
    expect(screen.getByText('Pergunta salva')).toBeVisible()
    mockConversationValue({
      ...conversationState,
      isReadingMessages: true,
      isReadingOlderMessages: true,
    })
    rerender(<Conversation />)
    expect(
      screen.getByRole('button', { name: 'Carregar mensagens anteriores' }),
    ).toBeDisabled()
    expect(screen.getByText('Carregando mensagens anteriores…')).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    expect(refresh).toHaveBeenCalledOnce()
  })
  it('renders approved Markdown safely and preserves learner text with accessible retry', () => {
    const response = {
      attemptId: 'attempt',
      learnerMessageId: 'learner',
      status: 'failed' as const,
      blocks: [
        {
          blockKey: 'block',
          ordinal: 0,
          intent: null,
          content:
            '**Explicação**\n\n<script>alert(1)</script>\n\n[perigoso](javascript:alert(1))\n\n```js\nconst result = 42\n```',
          sources: [],
        },
      ],
      consultations: ['learning'],
      lastSequence: 2,
      failureCode: 'unavailable',
    }
    const retryResponse = vi.fn()
    const value = {
      ...mentorValue,
      response,
      retryResponse,
      shouldAnimateBlock: vi.fn(() => false),
      markBlockPresented: vi.fn(),
      selectedSessionId: 'session',
      sessionDetail: {
        session: {
          id: 'session',
          title: 'Conversa',
          createdAt: '',
          updatedAt: '',
          lastActivityAt: '',
        },
        messages: {
          items: [
            {
              id: 'learner',
              sessionId: 'session',
              role: 'learner' as const,
              content: '  Mensagem preservada  ',
              createdAt: '',
              inReplyToMessageId: null,
              attachments: [],
            },
          ],
          nextCursor: null,
        },
        pendingLearnerMessageId: 'learner',
        response,
      },
      handleScroll: vi.fn(),
      scrollRef: { current: null },
    }
    useMentorContextMock.mockReturnValue(value)
    mockConversationValue(value)
    const { container } = render(<Conversation />)
    expect(screen.getByText('Mensagem preservada')).toBeVisible()
    expect(screen.getByText('Explicação')).toBeVisible()
    expect(container.querySelector('script')).toBeNull()
    expect(screen.getByText('perigoso').getAttribute('href')).not.toContain('javascript:')
    expect(screen.getByLabelText('Trecho de código')).toHaveTextContent(
      'const result = 42',
    )
    expect(screen.getByRole('status')).toHaveTextContent('Não foi possível concluir')
    expect(screen.getByRole('textbox')).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    expect(retryResponse).toHaveBeenCalledOnce()
  })
  it('keeps the typing presentation mounted when the persisted reply arrives', () => {
    const response: MentorResponseSnapshot = {
      attemptId: 'attempt',
      learnerMessageId: 'learner',
      status: 'processing',
      blocks: [
        {
          blockKey: 'block',
          ordinal: 0,
          intent: null,
          content: 'Resposta local persistida.',
          sources: [],
        },
      ],
      consultations: [],
      lastSequence: 1,
      failureCode: null,
    }
    const learnerMessage: MentorMessage = {
      id: 'learner',
      sessionId: 'session',
      role: 'learner',
      content: 'Pergunta local',
      inReplyToMessageId: null,
      createdAt: '',
      attachments: [],
    }
    const mentorReply: MentorMessage = {
      id: 'reply',
      sessionId: 'session',
      role: 'mentor',
      content: 'Resposta local persistida.',
      inReplyToMessageId: 'learner',
      createdAt: '',
      attachments: [],
    }
    const shouldAnimateBlock = vi.fn(() => true)
    const markBlockPresented = vi.fn()
    vi.useFakeTimers()
    try {
      useMentorContextMock.mockReturnValue({
        ...mentorValue,
        shouldAnimateBlock,
        markBlockPresented,
      } as unknown as MentorContextValue)
      const conversationState = {
        ...mentorValue,
        selectedSessionId: 'session',
        sessionDetail: {
          session: {
            id: 'session',
            title: 'Conversa',
            createdAt: '',
            updatedAt: '',
            lastActivityAt: '',
          },
          messages: { items: [learnerMessage], nextCursor: null },
          pendingLearnerMessageId: 'learner',
          response,
        },
        response,
        visibleMessages: [learnerMessage],
        handleScroll: vi.fn(),
        scrollRef: { current: null },
      }
      mockConversationValue(
        conversationState as unknown as ReturnType<typeof useConversation>,
      )
      const view = render(<Conversation />)
      act(() => vi.advanceTimersByTime(20))
      expect(screen.getByText('Resposta', { selector: 'p' })).toBeVisible()

      const completedResponse = { ...response, status: 'completed' as const }
      mockConversationValue({
        ...conversationState,
        sessionDetail: {
          ...conversationState.sessionDetail,
          messages: {
            items: [learnerMessage, mentorReply],
            nextCursor: null,
          },
          pendingLearnerMessageId: null,
          response: completedResponse,
        },
        response: completedResponse,
      } as unknown as ReturnType<typeof useConversation>)
      view.rerender(<Conversation />)

      expect(shouldAnimateBlock).toHaveBeenCalledOnce()
      expect(screen.getByText('Resposta', { selector: 'p' })).toBeVisible()
      act(() => vi.advanceTimersByTime(100))
      expect(
        screen.getByText('Resposta local persistida.', { selector: 'p' }),
      ).toBeVisible()
    } finally {
      cleanup()
      vi.useRealTimers()
    }
  })
  it.each(['queued', 'processing', 'cancelled', 'completed'] as const)(
    'exposes the appropriate response control for %s',
    (status) => {
      const cancelResponse = vi.fn()
      const retryResponse = vi.fn()
      const value = {
        ...mentorValue,
        cancelResponse,
        retryResponse,
        response: {
          attemptId: 'attempt',
          learnerMessageId: 'learner',
          status,
          blocks: [],
          consultations: ['unknown'],
          lastSequence: 1,
          failureCode: null,
        },
        handleScroll: vi.fn(),
        scrollRef: { current: null },
      }
      useMentorContextMock.mockReturnValue(value)
      mockConversationValue(value)
      render(<Conversation />)
      expect(screen.queryByText('Consultando informações autorizadas')).toBeNull()
      if (status === 'queued' || status === 'processing') {
        fireEvent.click(screen.getByRole('button', { name: 'Cancelar resposta' }))
        expect(cancelResponse).toHaveBeenCalledOnce()
      } else if (status === 'cancelled') {
        fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
        expect(retryResponse).toHaveBeenCalledOnce()
      } else {
        expect(screen.queryByRole('button', { name: 'Cancelar resposta' })).toBeNull()
        expect(screen.queryByRole('button', { name: 'Tentar novamente' })).toBeNull()
      }
    },
  )
  it('shows only the current executed workflow step and hides inferred context consultations', () => {
    const response: MentorResponseSnapshot = {
      attemptId: 'attempt',
      learnerMessageId: 'learner',
      status: 'processing',
      blocks: [],
      consultations: ['curriculum', 'learning'],
      lastSequence: 1,
      failureCode: null,
      progress: 'write-answer',
    }
    const value = {
      ...mentorValue,
      response,
      handleScroll: vi.fn(),
      scrollRef: { current: null },
    }
    useMentorContextMock.mockReturnValue(value)
    mockConversationValue(value)
    const { rerender } = render(<Conversation />)
    expect(screen.getByRole('status')).toHaveTextContent('Gerando resposta')
    expect(screen.queryByText('Consultando o currículo')).toBeNull()
    expect(screen.queryByText('Consultando sua aprendizagem')).toBeNull()
    mockConversationValue({
      ...value,
      response: { ...response, progress: 'review-answer' },
    })
    rerender(<Conversation />)
    expect(screen.getByRole('status')).toHaveTextContent('Revisando resposta')
    expect(screen.queryByText('Gerando resposta')).toBeNull()
    mockConversationValue({
      ...value,
      response: { ...response, status: 'failed' },
    })
    rerender(<Conversation />)
    expect(screen.getByRole('status')).toHaveTextContent('Não foi possível concluir')
    expect(screen.queryByText('Revisando resposta')).toBeNull()
  })
})
