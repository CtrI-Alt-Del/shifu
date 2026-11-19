import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ROUTES } from '@/constants/routes'
import type { MentorContextValue } from '@/ui/intelligence/contexts/mentor-context/types'
import { useAiQuotaBlock } from '@/ui/intelligence/hooks/use-ai-quota-block'
import { useMentorContext } from '@/ui/intelligence/hooks/use-mentor-context'
import type { AnchorProps } from '@/ui/shared/widgets/components/anchor'
import { MentorChat } from '..'
import { useMentorChat } from '../use-mentor-chat'

// Entrance motion settles at once, so visibility assertions see the final
// state; the shared entrance owns its animated cases.
vi.mock('@/ui/shared/hooks/use-reduced-motion-preference', () => ({
  useReducedMotionPreference: vi.fn(() => ({ prefersReducedMotion: true })),
}))
vi.mock('../use-mentor-chat', () => ({ useMentorChat: vi.fn() }))
vi.mock('@/ui/shared/widgets/components/anchor', () => ({
  Anchor: ({ children, route, search: _search, ...props }: AnchorProps) => (
    <a href={ROUTES[route]} {...props}>
      {typeof children === 'function' ? children({ isActive: false }) : children}
    </a>
  ),
}))
vi.mock('@/ui/intelligence/hooks/use-mentor-context', () => ({
  useMentorContext: vi.fn(),
}))
vi.mock('@/ui/intelligence/hooks/use-ai-quota-block', () => ({
  useAiQuotaBlock: vi.fn(),
}))
const useAiQuotaBlockMock = vi.mocked(useAiQuotaBlock)
const useMentorChatMock = vi.mocked(useMentorChat)
const useMentorContextMock = vi.mocked(useMentorContext)
const startNewMock = vi.fn()
const setDraftMock = vi.fn()
const sendFirstMessageMock = vi.fn()

const contextValue: MentorContextValue = {
  dictationStatus: 'idle',
  dictationError: null,
  dictationElapsedSeconds: 0,
  dictationLanguageAvailability: 'unavailable',
  dictationInstallationStatus: 'idle',
  dictationInstallationError: null,
  isDictationBusy: false,
  canStartDictation: false,
  canInstallDictationLanguage: false,
  startDictation: vi.fn(),
  finishDictation: vi.fn(),
  cancelDictation: vi.fn(),
  installDictationLanguage: vi.fn(),
  releaseDictationSurface: vi.fn(),
  response: null,
  isCancellingResponse: false,
  isRetryingResponse: false,
  submitMessage: vi.fn(),
  cancelResponse: vi.fn(),
  retryResponse: vi.fn(),
  shouldAnimateBlock: vi.fn(),
  markBlockPresented: vi.fn(),
  selectedSessionId: null,
  sessionDetail: null,
  summary: { current: null, failureAfterMessageId: null },
  isSummarizingContext: false,
  blockingActionProposalId: null,
  isRefreshingActions: false,
  hasActionRefreshTimedOut: false,
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
  isAiQuotaRefused: false,
  openPanel: vi.fn(),
  closePanel: vi.fn(),
  showPanelHistory: vi.fn(),
  showPanelConversation: vi.fn(),
  expandConversation: vi.fn(),
  startNewConversation: startNewMock,
  selectSession: vi.fn(),
  setDraft: setDraftMock,
  addAttachments: vi.fn(),
  retryAttachment: vi.fn(),
  removeAttachment: vi.fn(),
  setSearch: vi.fn(),
  sendFirstMessage: sendFirstMessageMock,
  loadMoreSessions: vi.fn(),
  loadOlderMessages: vi.fn(),
  revealMessage: vi.fn(),
  openRenameDialog: vi.fn(),
  openRemoveDialog: vi.fn(),
  closeDialog: vi.fn(),
  renameSession: vi.fn(),
  removeSession: vi.fn(),
  refresh: vi.fn(),
  refreshActions: vi.fn(),
  onActionResolved: vi.fn(),
}

const notBlockedQuota: ReturnType<typeof useAiQuotaBlock> = {
  isAiQuotaBlocked: false,
  isAiQuotaNearLimit: false,
  getAiQuotaBlockedMessage: () => 'Sua cota de IA acabou.',
  aiQuotaBlockedRole: 'status',
  aiQuotaAccountId: 'account-1',
  aiQuotaPercentage: 85,
  aiQuotaRenewsOn: '2026-12-01',
}

describe('MentorChat', () => {
  beforeEach(() => useAiQuotaBlockMock.mockReturnValue(notBlockedQuota))
  afterEach(cleanup)

  it.each(['page', 'fab'] as const)(
    'shows a private-content-free skeleton while validating %s',
    (surface) => {
      useMentorContextMock.mockReturnValue(contextValue)
      useMentorChatMock.mockReturnValue({
        ...contextValue,
        isValidatingScope: true,
        handleSelectSession: vi.fn(),
        handleStartNewConversation: vi.fn(),
        surface,
      })
      const { container } = render(<MentorChat surface={surface} />)
      expect(screen.getByRole('status')).toHaveTextContent('Confirmando sua sessão…')
      expect(container.querySelector('[data-slot="skeleton"]')).not.toBeNull()
      expect(screen.queryByRole('textbox')).toBeNull()
      expect(screen.queryByLabelText('Buscar conversa por título')).toBeNull()
    },
  )

  it('renders real history and composer children with the Memórias link and unavailable actions disabled', () => {
    useMentorContextMock.mockReturnValue(contextValue)
    useMentorChatMock.mockReturnValue({
      ...contextValue,
      handleSelectSession: vi.fn(),
      handleStartNewConversation: startNewMock,
      surface: 'page',
    })
    render(<MentorChat surface='page' />)
    expect(screen.getByRole('heading', { name: 'Nova conversa' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Como posso ajudar?' })).toBeVisible()
    expect(screen.getByLabelText('Buscar conversa por título')).toBeVisible()
    expect(
      screen.getByRole('button', {
        name: 'Anexar arquivo ou imagem',
      }),
    ).toBeEnabled()
    expect(
      screen.getByRole('button', { name: 'Gravar ditado. Indisponível no momento' }),
    ).toBeDisabled()
    expect(screen.getByRole('link', { name: 'Memórias' })).toHaveAttribute(
      'href',
      ROUTES.intelligenceMemories,
    )
    expect(screen.queryByRole('button', { name: /Cota de uso/ })).not.toBeInTheDocument()
    expect(screen.queryByText('IA · indisponível')).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Escreva sua mensagem para o Mentor'), {
      target: { value: 'Primeira mensagem' },
    })
    expect(setDraftMock).toHaveBeenCalledWith('Primeira mensagem')
  })

  it('shows scope validation and scope error feedback without private children', () => {
    useMentorContextMock.mockReturnValue(contextValue)
    useMentorChatMock.mockReturnValue({
      ...contextValue,
      isValidatingScope: true,
      handleSelectSession: vi.fn(),
      handleStartNewConversation: vi.fn(),
      surface: 'fab',
    })
    const { rerender } = render(<MentorChat surface='fab' />)
    expect(screen.getByText('Confirmando sua sessão…')).toBeVisible()
    expect(screen.queryByLabelText('Buscar conversa por título')).not.toBeInTheDocument()

    useMentorChatMock.mockReturnValue({
      ...contextValue,
      isValidatingScope: false,
      scopeError: 'Atualize a página.',
      handleSelectSession: vi.fn(),
      handleStartNewConversation: vi.fn(),
      surface: 'fab',
    })
    rerender(<MentorChat surface='fab' />)
    expect(screen.getByRole('alert')).toHaveTextContent('Atualize a página.')
  })

  it('renders history in the expanded page and switches the floating panel views', () => {
    useMentorContextMock.mockReturnValue(contextValue)
    const showHistory = vi.fn()
    const showConversation = vi.fn()
    useMentorChatMock.mockReturnValue({
      ...contextValue,
      panelView: 'history',
      showPanelHistory: showHistory,
      showPanelConversation: showConversation,
      handleSelectSession: vi.fn(),
      handleStartNewConversation: startNewMock,
      surface: 'fab',
    })
    const { rerender } = render(<MentorChat surface='fab' />)
    expect(screen.getByRole('region', { name: 'Histórico de conversas' })).toBeVisible()
    expect(screen.queryByLabelText('Conversa com o Mentor')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Nova conversa' })).toBeVisible()
    startNewMock.mockClear()
    screen.getByRole('button', { name: 'Nova conversa' }).click()
    expect(startNewMock).toHaveBeenCalled()
    expect(showHistory).not.toHaveBeenCalled()
    expect(showConversation).not.toHaveBeenCalled()
    screen.getByRole('button', { name: 'Voltar à conversa' }).click()
    expect(showConversation).toHaveBeenCalledOnce()

    useMentorChatMock.mockReturnValue({
      ...contextValue,
      panelView: 'conversation',
      handleSelectSession: vi.fn(),
      handleStartNewConversation: vi.fn(),
      surface: 'page',
    })
    rerender(<MentorChat surface='page' />)
    expect(
      screen.getAllByRole('region', { name: 'Histórico de conversas' }),
    ).toHaveLength(1)
    expect(screen.getByLabelText('Conversa com o Mentor')).toBeInTheDocument()
  })
  it('opens selected-session rename and returns from page history to the conversation', () => {
    const openRename = vi.fn()
    const showHistory = vi.fn()
    const showConversation = vi.fn()
    useMentorContextMock.mockReturnValue(contextValue)
    const value = {
      ...contextValue,
      sessionDetail: {
        session: { id: 'owned-session', title: 'Conversa salva' },
      } as NonNullable<MentorContextValue['sessionDetail']>,
      openRenameDialog: openRename,
      showPanelHistory: showHistory,
      showPanelConversation: showConversation,
      handleSelectSession: vi.fn(),
      handleStartNewConversation: startNewMock,
      surface: 'page' as const,
    }
    useMentorChatMock.mockReturnValue(value)
    const { rerender } = render(<MentorChat surface='page' />)
    fireEvent.click(screen.getByRole('button', { name: 'Renomear' }))
    expect(openRename).toHaveBeenCalledWith('owned-session')
    fireEvent.click(screen.getByRole('button', { name: 'Histórico de conversas' }))
    expect(showHistory).toHaveBeenCalledOnce()
    useMentorChatMock.mockReturnValue({ ...value, panelView: 'history' })
    rerender(<MentorChat surface='page' />)
    fireEvent.click(screen.getByRole('button', { name: 'Histórico de conversas' }))
    expect(showConversation).toHaveBeenCalledOnce()
    fireEvent.click(screen.getByRole('button', { name: 'Voltar à conversa' }))
    expect(showConversation).toHaveBeenCalledTimes(2)
  })
  it('routes sidebar new and selection actions through the page handlers', () => {
    const handleNew = vi.fn()
    const handleSelect = vi.fn().mockResolvedValue(undefined)
    const rawNew = vi.fn()
    const rawSelect = vi.fn()
    useMentorContextMock.mockReturnValue({
      ...contextValue,
      startNewConversation: rawNew,
      selectSession: rawSelect,
      sessionsPage: {
        items: [
          {
            id: 'owned',
            title: 'Conversa do histórico',
            createdAt: '2026-10-09T12:00:00Z',
            updatedAt: '2026-10-09T12:00:00Z',
            lastActivityAt: '2026-10-09T12:00:00Z',
          },
        ],
        nextCursor: null,
      },
    })
    useMentorChatMock.mockReturnValue({
      ...contextValue,
      handleSelectSession: handleSelect,
      handleStartNewConversation: handleNew,
      surface: 'page',
    })
    render(<MentorChat surface='page' />)
    fireEvent.click(screen.getByRole('button', { name: 'Nova conversa' }))
    fireEvent.click(screen.getByRole('button', { name: 'Conversa do histórico' }))
    expect(handleNew).toHaveBeenCalledOnce()
    expect(handleSelect).toHaveBeenCalledWith('owned')
    expect(rawNew).not.toHaveBeenCalled()
    expect(rawSelect).not.toHaveBeenCalled()
  })
  it('renders distinct draft and saved FAB headers and delegates panel controls', () => {
    useMentorContextMock.mockReturnValue(contextValue)
    const showHistory = vi.fn()
    const expand = vi.fn()
    const close = vi.fn()
    const value = {
      ...contextValue,
      showPanelHistory: showHistory,
      expandConversation: expand,
      closePanel: close,
      handleSelectSession: vi.fn(),
      handleStartNewConversation: vi.fn(),
      surface: 'fab' as const,
    }
    useMentorChatMock.mockReturnValue(value)
    const { rerender } = render(<MentorChat surface='fab' />)
    expect(screen.getByRole('heading', { name: 'Mentor', level: 1 })).toBeVisible()
    expect(screen.getByText('Ajuda para continuar aprendendo')).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Histórico de conversas' }))
    expect(showHistory).toHaveBeenCalledOnce()
    useMentorChatMock.mockReturnValue({
      ...value,
      sessionDetail: {
        session: { id: 'saved-session', title: 'Conversa salva' },
      } as NonNullable<MentorContextValue['sessionDetail']>,
    })
    rerender(<MentorChat surface='fab' />)
    expect(
      screen.getByRole('heading', { name: 'Conversa salva', level: 1 }),
    ).toBeVisible()
    expect(screen.queryByText('Ajuda para continuar aprendendo')).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Memórias' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Histórico de conversas' }))
    fireEvent.click(screen.getByRole('button', { name: 'Expandir conversa' }))
    fireEvent.click(screen.getByRole('button', { name: 'Fechar painel do Mentor' }))
    expect(showHistory).toHaveBeenCalledTimes(2)
    expect(expand).toHaveBeenCalledOnce()
    expect(close).toHaveBeenCalledOnce()
  })
  it('blocks only the AI controls at the quota limit and keeps history, rename and delete working', () => {
    const sendFirstMessage = vi.fn()
    const retryResponse = vi.fn()
    const openRename = vi.fn()
    const openRemove = vi.fn()
    const selectSession = vi.fn().mockResolvedValue(undefined)
    useAiQuotaBlockMock.mockReturnValue({
      ...notBlockedQuota,
      isAiQuotaBlocked: true,
      getAiQuotaBlockedMessage: () => 'Sua cota de IA acabou. Volta em 1 de dezembro.',
    })
    const session = {
      id: 'owned',
      title: 'Conversa salva',
      createdAt: '2026-10-09T12:00:00Z',
      updatedAt: '2026-10-09T12:00:00Z',
      lastActivityAt: '2026-10-09T12:00:00Z',
    }
    const value = {
      ...contextValue,
      selectedSessionId: 'owned',
      sessionDetail: {
        session,
        messages: { items: [], nextCursor: null },
        pendingLearnerMessageId: null,
      } as unknown as NonNullable<MentorContextValue['sessionDetail']>,
      response: {
        attemptId: 'attempt-1',
        learnerMessageId: 'learner-1',
        status: 'failed',
        blocks: [],
        consultations: [],
        lastSequence: 2,
        failureCode: null,
      } as MentorContextValue['response'],
      draft: 'Mensagem preservada',
      canStartDictation: true,
      sessionsPage: { items: [session], nextCursor: null },
      sendFirstMessage,
      retryResponse,
      openRenameDialog: openRename,
      openRemoveDialog: openRemove,
      selectSession,
    }
    useMentorContextMock.mockReturnValue(value)
    useMentorChatMock.mockReturnValue({
      ...value,
      handleSelectSession: selectSession,
      handleStartNewConversation: startNewMock,
      surface: 'page',
    })
    render(<MentorChat surface='page' />)

    expect(
      screen.getByText('Sua cota de IA acabou. Volta em 1 de dezembro.'),
    ).toBeVisible()
    expect(screen.getByRole('link', { name: 'Ver uso da IA' })).toHaveAttribute(
      'href',
      ROUTES.accountAiUsage,
    )
    for (const control of [
      screen.getByRole('button', { name: 'Enviar' }),
      screen.getByRole('button', { name: 'Anexar arquivo ou imagem' }),
      screen.getByRole('button', { name: /Gravar ditado/ }),
      screen.getByRole('button', { name: 'Tentar novamente' }),
    ]) {
      expect(control).toHaveAttribute('aria-disabled', 'true')
      expect(control).toHaveAccessibleDescription(/Sua cota de IA acabou/)
      fireEvent.click(control)
    }
    expect(screen.getByLabelText('Escreva sua mensagem para o Mentor')).toHaveAttribute(
      'placeholder',
      'Envio pausado até a renovação da cota',
    )
    expect(sendFirstMessage).not.toHaveBeenCalled()
    expect(retryResponse).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: 'Renomear' }))
    fireEvent.click(screen.getByRole('button', { name: 'Renomear Conversa salva' }))
    fireEvent.click(screen.getByRole('button', { name: 'Excluir Conversa salva' }))
    fireEvent.click(screen.getByRole('button', { name: /^Conversa salva/ }))
    expect(openRename).toHaveBeenCalledTimes(2)
    expect(openRemove).toHaveBeenCalledWith('owned')
    expect(selectSession).toHaveBeenCalledWith('owned')
  })
})
