import { act, cleanup, render, renderHook, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement, useLayoutEffect } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type {
  MentorSessionDetail,
  MentorSessionsPage,
} from '@/rest/services/intelligence-service'
import { MentorContextProvider } from '..'
import { useMentorContext } from '@/ui/intelligence/hooks/use-mentor-context'

const mocks = vi.hoisted(() => ({
  create: vi.fn(),
  list: vi.fn(),
  detail: vi.fn(),
  rename: vi.fn(),
  remove: vi.fn(),
  navigate: vi.fn(),
  location: { pathname: '/gamification', search: {} as Record<string, unknown> },
}))

vi.mock('@tanstack/react-router', () => ({
  useLocation: () => mocks.location,
  useNavigate: () => mocks.navigate,
}))
vi.mock('@/ui/intelligence/hooks/mentor-server-functions', () => ({
  createMentorSessionServer: mocks.create,
  getMentorSessionServer: mocks.detail,
  listMentorSessionsServer: mocks.list,
  removeMentorSessionServer: mocks.remove,
  renameMentorSessionServer: mocks.rename,
}))

const sessionsPage: MentorSessionsPage = { items: [], nextCursor: null }
const detail: MentorSessionDetail = {
  session: {
    id: '01J7T8AC91Z5K8M4JQ8C2D6F0B',
    title: 'Primeira conversa',
    createdAt: '2026-10-08T12:00:00Z',
    updatedAt: '2026-10-08T12:00:00Z',
    lastActivityAt: '2026-10-08T12:00:00Z',
  },
  messages: { items: [], nextCursor: null },
  pendingLearnerMessageId: null,
}

const renderProvider = () => {
  const client = new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
      queries: { retry: false },
    },
  })
  return render(
    createElement(
      QueryClientProvider,
      { client },
      createElement(
        MentorContextProvider,
        { accountEmail: 'aluna@example.com' },
        createElement(Consumer),
      ),
    ),
  )
}

const Consumer = () => {
  const mentor = useMentorContext()
  return createElement(
    'div',
    null,
    createElement(
      'output',
      { 'aria-label': 'current title' },
      mentor.sessionDetail?.session.title ?? 'Nova conversa',
    ),
    createElement('output', { 'aria-label': 'submission error' }, mentor.submissionError),
    createElement(
      'button',
      { type: 'button', onClick: () => mentor.setDraft('  dúvida\ncom detalhes  ') },
      'Preparar mensagem',
    ),
    createElement(
      'button',
      { type: 'button', onClick: () => mentor.setDraft('') },
      'Limpar mensagem',
    ),
    createElement(
      'button',
      { type: 'button', onClick: () => mentor.setDraft('texto editado') },
      'Editar mensagem',
    ),
    createElement(
      'button',
      { type: 'button', onClick: () => void mentor.sendFirstMessage() },
      'Enviar mensagem',
    ),
    createElement(
      'button',
      { type: 'button', onClick: () => void mentor.refresh() },
      'Atualizar',
    ),
    createElement(
      'button',
      { type: 'button', onClick: () => void mentor.selectSession(detail.session.id) },
      'Selecionar conversa',
    ),
    createElement(
      'button',
      { type: 'button', onClick: () => void mentor.loadMoreSessions() },
      'Mais conversas',
    ),
    createElement(
      'button',
      { type: 'button', onClick: () => void mentor.loadOlderMessages() },
      'Mensagens anteriores',
    ),
    createElement(
      'button',
      { type: 'button', onClick: () => mentor.setSearch(' python ') },
      'Buscar',
    ),
    createElement(
      'button',
      { type: 'button', onClick: () => mentor.startNewConversation() },
      'Nova conversa',
    ),
    createElement(
      'button',
      { type: 'button', onClick: () => mentor.openRenameDialog(detail.session.id) },
      'Abrir renomear',
    ),
    createElement(
      'button',
      { type: 'button', onClick: () => void mentor.renameSession('Novo título') },
      'Renomear',
    ),
    createElement(
      'button',
      { type: 'button', onClick: () => mentor.openRemoveDialog(detail.session.id) },
      'Abrir remover',
    ),
    createElement(
      'button',
      { type: 'button', onClick: () => void mentor.removeSession() },
      'Remover',
    ),
    createElement(
      'button',
      { type: 'button', onClick: () => mentor.closeDialog() },
      'Fechar diálogo',
    ),
    createElement(
      'button',
      { type: 'button', onClick: () => mentor.showPanelHistory() },
      'Histórico',
    ),
    createElement(
      'button',
      { type: 'button', onClick: () => mentor.showPanelConversation() },
      'Conversa',
    ),
    createElement(
      'button',
      { type: 'button', onClick: () => mentor.openPanel() },
      'Abrir painel',
    ),
    createElement(
      'button',
      { type: 'button', onClick: () => mentor.closePanel() },
      'Fechar painel',
    ),
    createElement(
      'button',
      { type: 'button', onClick: () => void mentor.expandConversation() },
      'Expandir conversa',
    ),
    createElement('output', { 'aria-label': 'selected id' }, mentor.selectedSessionId),
    createElement(
      'output',
      { 'aria-label': 'reading messages' },
      String(mentor.isReadingMessages),
    ),
    createElement(
      'output',
      { 'aria-label': 'message order' },
      mentor.sessionDetail?.messages.items.map((item) => item.id).join(','),
    ),
    createElement('output', { 'aria-label': 'history error' }, mentor.historyError),
    createElement(
      'output',
      { 'aria-label': 'conversation error' },
      mentor.conversationError,
    ),
    createElement('output', { 'aria-label': 'scope error' }, mentor.scopeError),
    createElement('output', { 'aria-label': 'active dialog' }, mentor.activeDialog),
    createElement('output', { 'aria-label': 'search' }, mentor.search),
  )
}

const ScopeProbe = ({
  accountEmail,
  observed,
}: {
  accountEmail: string
  observed: Array<{ accountEmail: string; title: string | null }>
}) => {
  const mentor = useMentorContext()
  useLayoutEffect(() => {
    observed.push({ accountEmail, title: mentor.sessionDetail?.session.title ?? null })
  }, [accountEmail, mentor.sessionDetail, observed])
  return createElement(
    'div',
    null,
    createElement(
      'output',
      { 'aria-label': 'scope probe title' },
      mentor.sessionDetail?.session.title ?? 'Nova conversa',
    ),
    createElement(Consumer),
  )
}

describe('useMentorContextProvider', () => {
  afterEach(cleanup)

  beforeEach(() => {
    vi.resetAllMocks()
    mocks.location = { pathname: '/gamification', search: {} }
    mocks.list.mockResolvedValue(sessionsPage)
    mocks.detail.mockResolvedValue(detail)
    mocks.create
      .mockRejectedValueOnce(new Error('transport failed'))
      .mockResolvedValue(detail)
    mocks.rename.mockResolvedValue(detail.session)
    mocks.remove.mockResolvedValue(undefined)
    vi.stubGlobal('crypto', {
      randomUUID: vi.fn(() => '4f8d5418-2f14-4a12-8d80-7a8c31b5bc50'),
    })
  })

  it('requires consumers to be mounted under the shared provider', () => {
    expect(() => renderHook(() => useMentorContext())).toThrow(
      'useMentorContext deve ser usado dentro de MentorContextProvider.',
    )
  })

  it('keeps a first message and its UUID key for an idempotent retry, then selects the accepted session', async () => {
    renderProvider()
    await waitFor(() => expect(mocks.list).toHaveBeenCalled())
    act(() => screen.getByRole('button', { name: 'Preparar mensagem' }).click())

    await act(async () => {
      screen.getByRole('button', { name: 'Enviar mensagem' }).click()
    })
    expect(screen.getByLabelText('submission error')).toHaveTextContent(
      'Não foi possível enviar',
    )
    await act(async () => {
      screen.getByRole('button', { name: 'Enviar mensagem' }).click()
    })

    expect(mocks.create).toHaveBeenNthCalledWith(1, {
      data: {
        accountEmail: 'aluna@example.com',
        submissionKey: '4f8d5418-2f14-4a12-8d80-7a8c31b5bc50',
        firstMessage: '  dúvida\ncom detalhes  ',
      },
    })
    expect(mocks.create).toHaveBeenNthCalledWith(2, {
      data: {
        accountEmail: 'aluna@example.com',
        submissionKey: '4f8d5418-2f14-4a12-8d80-7a8c31b5bc50',
        firstMessage: '  dúvida\ncom detalhes  ',
      },
    })
    await waitFor(() =>
      expect(screen.getByLabelText('current title')).toHaveTextContent(
        'Primeira conversa',
      ),
    )
  })

  it('re-fetches private history on window focus without retaining a query cache', async () => {
    renderProvider()
    await waitFor(() => expect(mocks.list).toHaveBeenCalled())
    const initialCount = mocks.list.mock.calls.length
    act(() => window.dispatchEvent(new Event('focus')))
    await waitFor(() =>
      expect(mocks.list.mock.calls.length).toBeGreaterThan(initialCount),
    )
  })

  it('covers history paging, selection, search and dialog actions on the shared context', async () => {
    const first = { ...detail.session, id: 'session-1' }
    mocks.list.mockResolvedValue({ items: [first], nextCursor: 'page-2' })
    mocks.detail.mockResolvedValue({
      ...detail,
      session: first,
      messages: { items: [], nextCursor: 'older' },
    })
    mocks.rename.mockResolvedValue({ ...first, title: 'Novo título' })
    const view = renderProvider()
    await waitFor(() => expect(mocks.list).toHaveBeenCalled())
    await act(async () => screen.getByRole('button', { name: 'Mais conversas' }).click())
    await waitFor(() =>
      expect(mocks.list).toHaveBeenLastCalledWith({
        data: {
          accountEmail: 'aluna@example.com',
          search: undefined,
          cursor: 'page-2',
        },
      }),
    )

    await act(async () =>
      screen.getByRole('button', { name: 'Selecionar conversa' }).click(),
    )
    expect(mocks.detail).toHaveBeenCalledWith({
      data: {
        accountEmail: 'aluna@example.com',
        sessionId: detail.session.id,
        cursor: undefined,
      },
    })
    await act(async () =>
      screen.getByRole('button', { name: 'Mensagens anteriores' }).click(),
    )
    expect(mocks.detail).toHaveBeenLastCalledWith({
      data: {
        accountEmail: 'aluna@example.com',
        sessionId: detail.session.id,
        cursor: 'older',
      },
    })

    act(() => screen.getByRole('button', { name: 'Buscar' }).click())
    await act(async () => new Promise((resolve) => setTimeout(resolve, 350)))
    await waitFor(() =>
      expect(mocks.list).toHaveBeenCalledWith({
        data: {
          accountEmail: 'aluna@example.com',
          search: ' python ',
          cursor: undefined,
        },
      }),
    )

    act(() => screen.getByRole('button', { name: 'Abrir renomear' }).click())
    expect(screen.getByLabelText('active dialog')).toHaveTextContent('rename')
    await act(async () => screen.getByRole('button', { name: 'Renomear' }).click())
    expect(mocks.rename).toHaveBeenCalledWith({
      data: {
        accountEmail: 'aluna@example.com',
        sessionId: detail.session.id,
        title: 'Novo título',
      },
    })
    await waitFor(() =>
      expect(screen.getByLabelText('active dialog')).toBeEmptyDOMElement(),
    )

    act(() => screen.getByRole('button', { name: 'Abrir remover' }).click())
    await act(async () => screen.getByRole('button', { name: 'Remover' }).click())
    expect(mocks.remove).toHaveBeenCalledWith({
      data: { accountEmail: 'aluna@example.com', sessionId: detail.session.id },
    })
    act(() => screen.getByRole('button', { name: 'Fechar diálogo' }).click())
    act(() => screen.getByRole('button', { name: 'Histórico' }).click())
    act(() => screen.getByRole('button', { name: 'Conversa' }).click())
    act(() => screen.getByRole('button', { name: 'Abrir painel' }).click())
    act(() => screen.getByRole('button', { name: 'Fechar painel' }).click())
    act(() => screen.getByRole('button', { name: 'Nova conversa' }).click())
    expect(screen.getByLabelText('selected id')).toBeEmptyDOMElement()
    view.unmount()
  })

  it('merges older message pages without duplicates and sorts them by timestamp', async () => {
    const latest = {
      id: 'message-latest',
      sessionId: detail.session.id,
      role: 'mentor' as const,
      content: 'Mais recente',
      inReplyToMessageId: null,
      createdAt: '2026-10-08T12:02:00Z',
    }
    const older = {
      id: 'message-older',
      sessionId: detail.session.id,
      role: 'learner' as const,
      content: 'Anterior',
      inReplyToMessageId: null,
      createdAt: '2026-10-08T12:00:00Z',
    }
    const middle = {
      id: 'message-middle',
      sessionId: detail.session.id,
      role: 'mentor' as const,
      content: 'No meio',
      inReplyToMessageId: null,
      createdAt: '2026-10-08T12:01:00Z',
    }
    const currentDetail = {
      ...detail,
      messages: { items: [latest], nextCursor: 'older' },
    }
    mocks.detail.mockResolvedValueOnce(currentDetail).mockResolvedValueOnce({
      ...detail,
      messages: { items: [latest, older, middle], nextCursor: null },
    })
    const view = renderProvider()
    await waitFor(() => expect(mocks.list).toHaveBeenCalled())
    await act(async () =>
      screen.getByRole('button', { name: 'Selecionar conversa' }).click(),
    )
    await act(async () =>
      screen.getByRole('button', { name: 'Mensagens anteriores' }).click(),
    )
    expect(mocks.detail).toHaveBeenNthCalledWith(2, {
      data: {
        accountEmail: 'aluna@example.com',
        sessionId: detail.session.id,
        cursor: 'older',
      },
    })
    await waitFor(() =>
      expect(screen.getByLabelText('message order')).toHaveTextContent(
        'message-older,message-middle,message-latest',
      ),
    )
    view.unmount()
  })

  it('refreshes the selected session once before expanding without dropping the selection', async () => {
    renderProvider()
    await waitFor(() => expect(mocks.list).toHaveBeenCalled())
    await act(async () =>
      screen.getByRole('button', { name: 'Selecionar conversa' }).click(),
    )
    await waitFor(() => expect(mocks.detail).toHaveBeenCalledTimes(1))
    await act(async () =>
      screen.getByRole('button', { name: 'Expandir conversa' }).click(),
    )
    await waitFor(() => expect(mocks.detail).toHaveBeenCalledTimes(2))
    expect(mocks.navigate).toHaveBeenCalledWith({
      to: '/intelligence',
      search: { session: detail.session.id },
    })
    expect(screen.getByLabelText('selected id')).toHaveTextContent(detail.session.id)
  })

  it('leaves a ready blank draft when a pending detail request is superseded', async () => {
    let resolveDetail!: (value: MentorSessionDetail) => void
    mocks.detail.mockReturnValueOnce(
      new Promise<MentorSessionDetail>((resolve) => {
        resolveDetail = resolve
      }),
    )
    const view = renderProvider()
    await waitFor(() => expect(mocks.list).toHaveBeenCalled())
    act(() => screen.getByRole('button', { name: 'Selecionar conversa' }).click())
    await waitFor(() =>
      expect(screen.getByLabelText('reading messages')).toHaveTextContent('true'),
    )

    act(() => screen.getByRole('button', { name: 'Nova conversa' }).click())

    expect(screen.getByLabelText('reading messages')).toHaveTextContent('false')
    expect(screen.getByLabelText('current title')).toHaveTextContent('Nova conversa')
    expect(screen.getByLabelText('selected id')).toBeEmptyDOMElement()
    await act(async () => resolveDetail(detail))
    expect(screen.getByLabelText('reading messages')).toHaveTextContent('false')
    expect(screen.getByLabelText('current title')).toHaveTextContent('Nova conversa')
    view.unmount()
  })

  it('masks the previous account history on the first render after a scope switch', async () => {
    const client = new QueryClient({
      defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
    })
    const observed: Array<{ accountEmail: string; title: string | null }> = []
    const renderScope = (accountEmail: string) =>
      createElement(
        QueryClientProvider,
        { client },
        createElement(
          MentorContextProvider,
          { accountEmail },
          createElement(ScopeProbe, { accountEmail, observed }),
        ),
      )
    const view = render(renderScope('aluna@example.com'))
    await waitFor(() => expect(mocks.list).toHaveBeenCalled())
    await act(async () =>
      screen.getByRole('button', { name: 'Selecionar conversa' }).click(),
    )
    await waitFor(() =>
      expect(screen.getByLabelText('scope probe title')).toHaveTextContent(
        'Primeira conversa',
      ),
    )

    act(() => view.rerender(renderScope('outra@example.com')))

    expect(
      observed.find((item) => item.accountEmail === 'outra@example.com')?.title,
    ).toBeNull()
    view.unmount()
  })

  it('clears detail loading when a selected session is deleted during a pending read', async () => {
    let resolveDetail!: (value: MentorSessionDetail) => void
    mocks.detail.mockReturnValueOnce(
      new Promise<MentorSessionDetail>((resolve) => {
        resolveDetail = resolve
      }),
    )
    const view = renderProvider()
    await waitFor(() => expect(mocks.list).toHaveBeenCalled())
    act(() => screen.getByRole('button', { name: 'Selecionar conversa' }).click())
    await waitFor(() =>
      expect(screen.getByLabelText('reading messages')).toHaveTextContent('true'),
    )
    act(() => screen.getByRole('button', { name: 'Abrir remover' }).click())
    await act(async () => screen.getByRole('button', { name: 'Remover' }).click())

    expect(screen.getByLabelText('reading messages')).toHaveTextContent('false')
    expect(screen.getByLabelText('conversation error')).toBeEmptyDOMElement()
    expect(screen.getByLabelText('current title')).toHaveTextContent('Nova conversa')
    await act(async () => resolveDetail(detail))
    expect(screen.getByLabelText('reading messages')).toHaveTextContent('false')
    expect(screen.getByLabelText('current title')).toHaveTextContent('Nova conversa')
    view.unmount()
  })

  it('removes a deleted selected session from the Intelligence URL and keeps a new draft', async () => {
    mocks.location = {
      pathname: '/intelligence',
      search: { session: detail.session.id },
    }
    const view = renderProvider()
    await waitFor(() => expect(mocks.list).toHaveBeenCalled())
    await act(async () =>
      screen.getByRole('button', { name: 'Selecionar conversa' }).click(),
    )
    act(() => screen.getByRole('button', { name: 'Abrir remover' }).click())
    await act(async () => screen.getByRole('button', { name: 'Remover' }).click())
    await waitFor(() =>
      expect(mocks.navigate).toHaveBeenCalledWith({
        to: '/intelligence',
        search: { session: undefined },
        replace: true,
      }),
    )
    expect(screen.getByLabelText('selected id')).toBeEmptyDOMElement()
    expect(screen.getByLabelText('current title')).toHaveTextContent('Nova conversa')
    view.unmount()
  })

  it('keeps detail failures recoverable and clears scope-private selections', async () => {
    mocks.detail.mockRejectedValue(new Error('temporary detail outage'))
    const view = renderProvider()
    await waitFor(() => expect(mocks.list).toHaveBeenCalled())
    await act(async () =>
      screen.getByRole('button', { name: 'Selecionar conversa' }).click(),
    )
    await waitFor(() =>
      expect(screen.getByLabelText('conversation error')).toHaveTextContent(
        'Não foi possível carregar',
      ),
    )
    mocks.detail.mockRejectedValue(new Error('A sessão expirou'))
    await act(async () =>
      screen.getByRole('button', { name: 'Selecionar conversa' }).click(),
    )
    await waitFor(() =>
      expect(screen.getByLabelText('scope error')).toHaveTextContent(
        'Não foi possível confirmar',
      ),
    )
    expect(screen.getByLabelText('selected id')).toBeEmptyDOMElement()
    view.unmount()
  })

  it('keeps ordinary history failures recoverable and clears private data on scope failures', async () => {
    mocks.list.mockRejectedValue(new Error('temporary outage'))
    const view = renderProvider()
    await waitFor(() =>
      expect(screen.getByLabelText('history error')).toHaveTextContent(
        'Não foi possível carregar',
      ),
    )
    mocks.list.mockRejectedValue(new Error('A sessão da conta mudou'))
    await act(async () => screen.getByRole('button', { name: 'Atualizar' }).click())
    await waitFor(() =>
      expect(screen.getByLabelText('scope error')).toHaveTextContent(
        'Não foi possível confirmar',
      ),
    )
    expect(screen.getByLabelText('selected id')).toBeEmptyDOMElement()
    view.unmount()
  })

  it('guards empty sends and paging without cursors and expands as a new conversation', async () => {
    renderProvider()
    await waitFor(() => expect(mocks.list).toHaveBeenCalled())
    const createCalls = mocks.create.mock.calls.length
    const listCalls = mocks.list.mock.calls.length
    const detailCalls = mocks.detail.mock.calls.length
    await act(async () => screen.getByRole('button', { name: 'Enviar mensagem' }).click())
    await act(async () => screen.getByRole('button', { name: 'Mais conversas' }).click())
    await act(async () =>
      screen.getByRole('button', { name: 'Mensagens anteriores' }).click(),
    )
    await act(async () => screen.getByRole('button', { name: 'Renomear' }).click())
    await act(async () => screen.getByRole('button', { name: 'Remover' }).click())
    expect(mocks.create).toHaveBeenCalledTimes(createCalls)
    expect(mocks.detail).toHaveBeenCalledTimes(detailCalls)
    expect(mocks.rename).not.toHaveBeenCalled()
    expect(mocks.remove).not.toHaveBeenCalled()
    expect(mocks.list).toHaveBeenCalledTimes(listCalls)
    act(() => screen.getByRole('button', { name: 'Limpar mensagem' }).click())
    act(() => screen.getByRole('button', { name: 'Buscar' }).click())
    act(() => screen.getByRole('button', { name: 'Buscar' }).click())
    await act(async () =>
      screen.getByRole('button', { name: 'Expandir conversa' }).click(),
    )
    expect(mocks.navigate).toHaveBeenCalledWith({
      to: '/intelligence',
      search: { session: undefined },
    })
  })

  it('changes an idempotency key only when editing a failed message and handles create scope errors', async () => {
    vi.stubGlobal('crypto', {
      randomUUID: vi
        .fn()
        .mockReturnValueOnce('key-before-edit')
        .mockReturnValueOnce('key-after-edit'),
    })
    const view = renderProvider()
    await waitFor(() => expect(mocks.list).toHaveBeenCalled())
    act(() => screen.getByRole('button', { name: 'Preparar mensagem' }).click())
    await act(async () => screen.getByRole('button', { name: 'Enviar mensagem' }).click())
    await waitFor(() =>
      expect(screen.getByLabelText('submission error')).toHaveTextContent(
        'Não foi possível enviar',
      ),
    )
    act(() => screen.getByRole('button', { name: 'Editar mensagem' }).click())
    mocks.create.mockRejectedValueOnce(new Error('A sessão da conta mudou'))
    await act(async () => screen.getByRole('button', { name: 'Enviar mensagem' }).click())
    expect(mocks.create.mock.calls[1]?.[0].data.submissionKey).not.toBe(
      mocks.create.mock.calls[0]?.[0].data.submissionKey,
    )
    await waitFor(() =>
      expect(screen.getByLabelText('scope error')).toHaveTextContent(
        'Não foi possível confirmar',
      ),
    )
    view.unmount()
  })
})
