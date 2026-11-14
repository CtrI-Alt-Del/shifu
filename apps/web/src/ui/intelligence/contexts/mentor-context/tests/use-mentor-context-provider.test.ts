import { useMentorContextProvider } from '../use-mentor-context-provider'
import { LearnerMemoryFaker } from '@/core/intelligence/fakers/learner-memory-faker'
import type { MentorActionProposal } from '@/core/intelligence/mentor-action-proposal'
import type { MentorResponseSnapshot } from '@/core/intelligence/mentor-response'
import { act, cleanup, render, renderHook, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query'
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
  submit: vi.fn(),
  cancel: vi.fn(),
  retry: vi.fn(),
  createAttachmentBatch: vi.fn(),
  resetAttachmentBatch: vi.fn(),
  uploadAttachment: vi.fn(),
  removeAttachment: vi.fn(),
  attachmentBatch: null as null | Record<string, unknown>,
  attachmentBatchError: null as unknown,
  location: { pathname: '/gamification', search: {} as Record<string, unknown> },
}))

vi.mock('@tanstack/react-router', () => ({
  useLocation: () => mocks.location,
  useNavigate: () => mocks.navigate,
}))
vi.mock('@/ui/intelligence/hooks/use-create-mentor-session-action', async () => {
  const { useMutation } = await import('@tanstack/react-query')
  return {
    useCreateMentorSessionAction: (accountEmail: string) => {
      const mutation = useMutation({
        mutationFn: (input: unknown) =>
          mocks.create({ data: { accountEmail, ...(input as object) } }),
      })
      return {
        createMentorSession: mutation.mutateAsync,
        isCreatingMentorSession: mutation.isPending,
        resetCreateMentorSession: mutation.reset,
      }
    },
  }
})
vi.mock('@/ui/intelligence/hooks/use-mentor-session-query', async () => {
  const { useCallback } = await import('react')
  return {
    useMentorSessionQuery: (accountEmail: string) => ({
      readMentorSession: useCallback(
        (sessionId: string, cursor?: string) =>
          mocks.detail({ data: { accountEmail, sessionId, cursor } }),
        [accountEmail],
      ),
    }),
  }
})
vi.mock('@/ui/intelligence/hooks/use-mentor-sessions-query', async () => {
  const { useCallback } = await import('react')
  return {
    useMentorSessionsQuery: (accountEmail: string) => ({
      readMentorSessions: useCallback(
        (input: unknown) => mocks.list({ data: { accountEmail, ...(input as object) } }),
        [accountEmail],
      ),
    }),
  }
})
vi.mock('@/ui/intelligence/hooks/use-rename-mentor-session-action', () => ({
  useRenameMentorSessionAction: () => ({
    renameMentorSession: mocks.rename,
    resetRenameMentorSession: vi.fn(),
  }),
}))
vi.mock('@/ui/intelligence/hooks/use-remove-mentor-session-action', () => ({
  useRemoveMentorSessionAction: () => ({
    removeMentorSession: mocks.remove,
    resetRemoveMentorSession: vi.fn(),
  }),
}))
vi.mock('@/ui/intelligence/hooks/use-submit-mentor-message-action', () => ({
  useSubmitMentorMessageAction: () => ({
    submitMentorMessage: mocks.submit,
    isPending: false,
  }),
}))
vi.mock('@/ui/intelligence/hooks/use-create-mentor-attachment-batch-action', () => ({
  useCreateMentorAttachmentBatchAction: () => ({
    createMentorAttachmentBatch: mocks.createAttachmentBatch,
    resetCreateMentorAttachmentBatch: mocks.resetAttachmentBatch,
  }),
}))
vi.mock('@/ui/intelligence/hooks/use-upload-mentor-attachment-action', () => ({
  useUploadMentorAttachmentAction: () => ({
    uploadMentorAttachment: mocks.uploadAttachment,
  }),
}))
vi.mock('@/ui/intelligence/hooks/use-remove-mentor-attachment-action', () => ({
  useRemoveMentorAttachmentAction: () => ({
    removeMentorAttachment: mocks.removeAttachment,
  }),
}))
vi.mock('@/ui/intelligence/hooks/use-mentor-attachment-batch-query', () => ({
  useMentorAttachmentBatchQuery: () => ({
    mentorAttachmentBatch: mocks.attachmentBatch,
    mentorAttachmentBatchError: mocks.attachmentBatchError,
  }),
}))
vi.mock('@/ui/intelligence/hooks/use-cancel-mentor-response-action', () => ({
  useCancelMentorResponseAction: () => ({
    cancelMentorResponse: mocks.cancel,
    isPending: false,
  }),
}))
vi.mock('@/ui/intelligence/hooks/use-retry-mentor-response-action', () => ({
  useRetryMentorResponseAction: () => ({
    retryMentorResponse: mocks.retry,
    isPending: false,
  }),
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
  summary: { current: null, failureAfterMessageId: null },
  memoryItems: [],
  actionItems: [],
}
const readyAttachment = {
  attachmentId: '01J7T8AC91Z5K8M4JQ8C2D6F0D',
  filename: 'resumo.txt',
  mediaType: 'text/plain',
  sizeBytes: 5,
  status: 'ready' as const,
  failureCode: null,
  analyzedPages: [],
  illegiblePages: [],
  uninterpretedPages: [],
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
      {
        type: 'button',
        onClick: () =>
          void mentor.addAttachments([
            new File(['texto'], 'resumo.txt', { type: 'text/plain' }),
          ]),
      },
      'Anexar arquivo de teste',
    ),
    createElement(
      'button',
      {
        type: 'button',
        onClick: () =>
          void mentor.retryAttachment(mentor.draftAttachments[0]?.localKey ?? ''),
      },
      'Tentar novamente o envio',
    ),
    createElement(
      'button',
      {
        type: 'button',
        onClick: () =>
          void mentor.addAttachments([
            new File([new Uint8Array(2_000_000)], 'limite.txt', { type: 'text/plain' }),
            new File([new Uint8Array(2_000_001)], 'acima.txt', { type: 'text/plain' }),
            new File(['x'], 'programa.exe', { type: 'application/octet-stream' }),
            new File([], 'vazio.txt', { type: 'text/plain' }),
          ]),
      },
      'Anexar arquivos de limite',
    ),
    createElement(
      'button',
      {
        type: 'button',
        onClick: () =>
          void mentor.addAttachments(
            Array.from(
              { length: 6 },
              (_, index) =>
                new File([`arquivo ${index + 1}`], `arquivo-${index + 1}.txt`, {
                  type: 'text/plain',
                }),
            ),
          ),
      },
      'Anexar seis arquivos',
    ),
    createElement(
      'button',
      {
        type: 'button',
        onClick: () =>
          void mentor.removeAttachment(mentor.draftAttachments[0]?.localKey ?? ''),
      },
      'Remover primeiro anexo',
    ),
    createElement(
      'button',
      {
        type: 'button',
        onClick: () =>
          void mentor.removeAttachment(mentor.draftAttachments.at(-1)?.localKey ?? ''),
      },
      'Remover último anexo',
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
      { 'aria-label': 'draft attachments' },
      JSON.stringify(
        mentor.draftAttachments.map(({ attachment, error, file }) => ({
          filename: file.name,
          status: attachment?.status ?? null,
          error,
        })),
      ),
    ),
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
    mocks.createAttachmentBatch.mockResolvedValue({
      batchId: '01J7T8AC91Z5K8M4JQ8C2D6F0E',
      expiresAt: '2026-10-14T12:00:00Z',
      attachments: [],
    })
    mocks.uploadAttachment.mockResolvedValue(readyAttachment)
    mocks.removeAttachment.mockResolvedValue(undefined)
    mocks.attachmentBatch = null
    mocks.attachmentBatchError = null
    mocks.rename.mockResolvedValue(detail.session)
    mocks.remove.mockResolvedValue(undefined)
    let uuidCount = 0
    vi.stubGlobal('crypto', {
      randomUUID: vi.fn(() => {
        uuidCount += 1
        return uuidCount === 1
          ? '4f8d5418-2f14-4a12-8d80-7a8c31b5bc50'
          : `00000000-0000-4000-8000-${uuidCount.toString(16).padStart(12, '0')}`
      }),
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
        contextHint: null,
        submissionKey: '4f8d5418-2f14-4a12-8d80-7a8c31b5bc50',
        firstMessage: '  dúvida\ncom detalhes  ',
      },
    })
    expect(mocks.create).toHaveBeenNthCalledWith(2, {
      data: {
        accountEmail: 'aluna@example.com',
        contextHint: null,
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

  it('uploads ready files in the shared draft and retries a failed text submission with the same attachment IDs', async () => {
    renderProvider()
    await waitFor(() => expect(mocks.list).toHaveBeenCalled())
    act(() => screen.getByRole('button', { name: 'Preparar mensagem' }).click())
    await act(async () =>
      screen.getByRole('button', { name: 'Anexar arquivo de teste' }).click(),
    )
    await waitFor(() =>
      expect(screen.getByLabelText('draft attachments')).toHaveTextContent('ready'),
    )
    expect(mocks.createAttachmentBatch).toHaveBeenCalledWith(null)
    expect(mocks.uploadAttachment).toHaveBeenCalledWith(
      expect.objectContaining({
        batchId: '01J7T8AC91Z5K8M4JQ8C2D6F0E',
        file: expect.objectContaining({ name: 'resumo.txt' }),
      }),
    )
    mocks.attachmentBatch = {
      batchId: '01J7T8AC91Z5K8M4JQ8C2D6F0E',
      expiresAt: '2026-10-14T12:00:00Z',
      attachments: [{ ...readyAttachment, status: 'processing' }],
    }
    act(() => screen.getByRole('button', { name: 'Editar mensagem' }).click())
    expect(screen.getByLabelText('draft attachments')).toHaveTextContent('ready')
    mocks.attachmentBatch = null
    act(() => screen.getByRole('button', { name: 'Preparar mensagem' }).click())

    await act(async () => screen.getByRole('button', { name: 'Enviar mensagem' }).click())
    expect(screen.getByLabelText('draft attachments')).toHaveTextContent('ready')
    expect(screen.getByLabelText('submission error')).toHaveTextContent(
      'Não foi possível enviar',
    )
    await act(async () => screen.getByRole('button', { name: 'Enviar mensagem' }).click())

    const createCalls = mocks.create.mock.calls.map(([request]) => request.data)
    expect(createCalls).toHaveLength(2)
    for (const input of createCalls) {
      expect(input).toEqual(
        expect.objectContaining({
          attachmentBatchId: '01J7T8AC91Z5K8M4JQ8C2D6F0E',
          attachmentIds: [readyAttachment.attachmentId],
          firstMessage: '  dúvida\ncom detalhes  ',
        }),
      )
    }
    expect(screen.getByLabelText('draft attachments')).toHaveTextContent('[]')
  })

  it('reuses an upload key when retrying a failed attachment draft', async () => {
    mocks.uploadAttachment
      .mockRejectedValueOnce(new Error('connection lost'))
      .mockResolvedValue(readyAttachment)
    renderProvider()
    await waitFor(() => expect(mocks.list).toHaveBeenCalled())

    await act(async () =>
      screen.getByRole('button', { name: 'Anexar arquivo de teste' }).click(),
    )
    await waitFor(() =>
      expect(screen.getByLabelText('draft attachments')).toHaveTextContent(
        'Não foi possível enviar',
      ),
    )
    const firstUpload = mocks.uploadAttachment.mock.calls[0]?.[0] as {
      uploadKey: string
    }

    await act(async () =>
      screen.getByRole('button', { name: 'Tentar novamente o envio' }).click(),
    )

    expect(mocks.uploadAttachment).toHaveBeenCalledTimes(2)
    expect(mocks.uploadAttachment.mock.calls[1]?.[0]).toMatchObject({
      uploadKey: firstUpload.uploadKey,
      file: expect.objectContaining({ name: 'resumo.txt' }),
    })
    await waitFor(() =>
      expect(screen.getByLabelText('draft attachments')).toHaveTextContent('ready'),
    )
  })

  it('retries batch creation for the same draft after a temporary failure', async () => {
    mocks.createAttachmentBatch
      .mockRejectedValueOnce(new Error('connection lost'))
      .mockResolvedValue({
        batchId: '01J7T8AC91Z5K8M4JQ8C2D6F0E',
        expiresAt: '2026-10-14T12:00:00Z',
        attachments: [],
      })
    renderProvider()
    await waitFor(() => expect(mocks.list).toHaveBeenCalled())

    await act(async () =>
      screen.getByRole('button', { name: 'Anexar arquivo de teste' }).click(),
    )
    await waitFor(() =>
      expect(screen.getByLabelText('draft attachments')).toHaveTextContent(
        'Não foi possível preparar o envio',
      ),
    )
    await act(async () =>
      screen.getByRole('button', { name: 'Tentar novamente o envio' }).click(),
    )

    await waitFor(() => expect(mocks.uploadAttachment).toHaveBeenCalledOnce())
    expect(mocks.createAttachmentBatch).toHaveBeenCalledTimes(2)
    await waitFor(() =>
      expect(screen.getByLabelText('draft attachments')).toHaveTextContent('ready'),
    )
  })

  it('keeps the text when an upload fails, blocks send, and recovers after removing and re-adding the file', async () => {
    mocks.uploadAttachment
      .mockRejectedValueOnce(new Error('temporary upload failure'))
      .mockResolvedValueOnce(readyAttachment)
    renderProvider()
    await waitFor(() => expect(mocks.list).toHaveBeenCalled())
    act(() => screen.getByRole('button', { name: 'Preparar mensagem' }).click())
    await act(async () =>
      screen.getByRole('button', { name: 'Anexar arquivo de teste' }).click(),
    )
    await waitFor(() =>
      expect(screen.getByLabelText('draft attachments')).toHaveTextContent(
        'Não foi possível enviar o arquivo',
      ),
    )
    expect(screen.getByLabelText('submission error')).toBeEmptyDOMElement()
    expect(mocks.create).not.toHaveBeenCalled()

    await act(async () =>
      screen.getByRole('button', { name: 'Remover primeiro anexo' }).click(),
    )
    expect(screen.getByLabelText('draft attachments')).toHaveTextContent('[]')
    await act(async () =>
      screen.getByRole('button', { name: 'Anexar arquivo de teste' }).click(),
    )
    await waitFor(() =>
      expect(screen.getByLabelText('draft attachments')).toHaveTextContent('ready'),
    )
    expect(mocks.uploadAttachment).toHaveBeenCalledTimes(2)
  })

  it('validates each file independently and accepts the exact 2 MB boundary', async () => {
    let localId = 0
    vi.stubGlobal('crypto', {
      randomUUID: vi.fn(() => `local-${++localId}`),
    })
    renderProvider()
    await waitFor(() => expect(mocks.list).toHaveBeenCalled())
    act(() => screen.getByRole('button', { name: 'Preparar mensagem' }).click())
    await act(async () =>
      screen.getByRole('button', { name: 'Anexar arquivos de limite' }).click(),
    )

    await waitFor(() =>
      expect(screen.getByLabelText('draft attachments')).toHaveTextContent('ready'),
    )
    const state = screen.getByLabelText('draft attachments').textContent ?? ''
    expect(state).toContain('acima.txt')
    expect(state).toContain('O arquivo excede o limite de 2 MB.')
    expect(state).toContain('programa.exe')
    expect(state).toContain('Formato não aceito.')
    expect(state).toContain('vazio.txt')
    expect(state).toContain('O arquivo está vazio.')
    expect(mocks.uploadAttachment).toHaveBeenCalledOnce()
    expect(mocks.uploadAttachment).toHaveBeenCalledWith(
      expect.objectContaining({
        file: expect.objectContaining({ name: 'limite.txt', size: 2_000_000 }),
      }),
    )
    await act(async () => screen.getByRole('button', { name: 'Enviar mensagem' }).click())
    expect(mocks.create).not.toHaveBeenCalled()
    expect(screen.getByLabelText('draft attachments')).toHaveTextContent('limite.txt')
  })

  it('uploads at most five selected files and requires removal of the sixth before send', async () => {
    let id = 0
    vi.stubGlobal('crypto', {
      randomUUID: vi.fn(() => `local-${++id}`),
    })
    mocks.uploadAttachment.mockImplementation(async ({ file }: { file: File }) => ({
      ...readyAttachment,
      attachmentId: `attachment-${file.name}`,
      filename: file.name,
      sizeBytes: file.size,
    }))
    renderProvider()
    await waitFor(() => expect(mocks.list).toHaveBeenCalled())
    act(() => screen.getByRole('button', { name: 'Preparar mensagem' }).click())
    await act(async () =>
      screen.getByRole('button', { name: 'Anexar seis arquivos' }).click(),
    )

    await waitFor(() =>
      expect(screen.getByLabelText('draft attachments')).toHaveTextContent(
        'Você pode anexar até cinco arquivos',
      ),
    )
    expect(mocks.uploadAttachment).toHaveBeenCalledTimes(5)
    await act(async () => screen.getByRole('button', { name: 'Enviar mensagem' }).click())
    expect(mocks.create).not.toHaveBeenCalled()

    await act(async () =>
      screen.getByRole('button', { name: 'Remover último anexo' }).click(),
    )
    await act(async () => screen.getByRole('button', { name: 'Enviar mensagem' }).click())
    await act(async () => screen.getByRole('button', { name: 'Enviar mensagem' }).click())
    const submittedIds = mocks.create.mock.calls.map(
      ([request]) => request.data.attachmentIds,
    )
    expect(submittedIds).toHaveLength(2)
    expect(submittedIds[0]).toHaveLength(5)
    expect(submittedIds[1]).toEqual(submittedIds[0])
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

  it('keeps the composer scope ready while window focus refreshes history and selected detail', async () => {
    const { result } = renderHook(() => useMentorContextProvider('aluna@example.com'), {
      wrapper: responseWrapper,
    })
    await waitFor(() => expect(result.current.isValidatingScope).toBe(false))
    await act(async () => result.current.selectSession(detail.session.id))
    act(() => result.current.setDraft('Mensagem ainda não enviada'))
    await act(async () =>
      result.current.addAttachments([
        new File(['texto'], 'resumo.txt', { type: 'text/plain' }),
      ]),
    )
    const attachment = result.current.draftAttachments[0]
    let resolveHistory!: (value: MentorSessionsPage) => void
    let resolveDetail!: (value: MentorSessionDetail) => void
    mocks.list.mockReturnValueOnce(
      new Promise<MentorSessionsPage>((resolve) => {
        resolveHistory = resolve
      }),
    )
    mocks.detail.mockReturnValueOnce(
      new Promise<MentorSessionDetail>((resolve) => {
        resolveDetail = resolve
      }),
    )
    const historyCalls = mocks.list.mock.calls.length
    const detailCalls = mocks.detail.mock.calls.length

    act(() => window.dispatchEvent(new Event('focus')))

    expect(mocks.list).toHaveBeenCalledTimes(historyCalls + 1)
    expect(mocks.detail).toHaveBeenCalledTimes(detailCalls + 1)
    expect(result.current.isValidatingScope).toBe(false)
    expect(result.current.isReadingMessages).toBe(true)
    expect(result.current.isReadingOlderMessages).toBe(false)
    expect(result.current.draft).toBe('Mensagem ainda não enviada')
    expect(result.current.draftAttachments).toEqual([attachment])
    expect(result.current.selectedSessionId).toBe(detail.session.id)
    await act(async () => {
      resolveHistory({
        items: [{ ...detail.session, title: 'Título atualizado' }],
        nextCursor: null,
      })
      resolveDetail({
        ...detail,
        session: { ...detail.session, title: 'Título atualizado' },
      })
    })
    expect(result.current.sessionsPage.items[0]?.title).toBe('Título atualizado')
    expect(result.current.sessionDetail?.session.title).toBe('Título atualizado')
    expect(result.current.isValidatingScope).toBe(false)
    expect(result.current.draftAttachments).toEqual([attachment])
  })

  it.each([
    ['history', 'A sessão da conta mudou'],
    ['detail', 'A sessão expirou'],
  ])(
    'clears private composer state when focus %s revalidation loses scope',
    async (boundary, message) => {
      const { result } = renderHook(() => useMentorContextProvider('aluna@example.com'), {
        wrapper: responseWrapper,
      })
      await waitFor(() => expect(result.current.isValidatingScope).toBe(false))
      await act(async () => result.current.selectSession(detail.session.id))
      act(() => result.current.setDraft('Mensagem privada'))
      await act(async () =>
        result.current.addAttachments([
          new File(['texto privado'], 'resumo.txt', { type: 'text/plain' }),
        ]),
      )
      expect(result.current.draftAttachments).toHaveLength(1)
      if (boundary === 'history') mocks.list.mockRejectedValueOnce(new Error(message))
      else mocks.detail.mockRejectedValueOnce(new Error(message))

      await act(async () => window.dispatchEvent(new Event('focus')))

      await waitFor(() =>
        expect(result.current.scopeError).toContain('Não foi possível confirmar'),
      )
      expect(result.current.selectedSessionId).toBeNull()
      expect(result.current.sessionDetail).toBeNull()
      expect(result.current.sessionsPage.items).toEqual([])
      expect(result.current.draft).toBe('')
      expect(result.current.draftAttachments).toEqual([])
    },
  )

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
      sessionId: detail.session.id,
      title: 'Novo título',
    })
    await waitFor(() =>
      expect(screen.getByLabelText('active dialog')).toBeEmptyDOMElement(),
    )

    act(() => screen.getByRole('button', { name: 'Abrir remover' }).click())
    await act(async () => screen.getByRole('button', { name: 'Remover' }).click())
    expect(mocks.remove).toHaveBeenCalledWith(detail.session.id)
    act(() => screen.getByRole('button', { name: 'Fechar diálogo' }).click())
    act(() => screen.getByRole('button', { name: 'Histórico' }).click())
    act(() => screen.getByRole('button', { name: 'Conversa' }).click())
    act(() => screen.getByRole('button', { name: 'Abrir painel' }).click())
    act(() => screen.getByRole('button', { name: 'Fechar painel' }).click())
    act(() => screen.getByRole('button', { name: 'Nova conversa' }).click())
    expect(screen.getByLabelText('selected id')).toBeEmptyDOMElement()
    view.unmount()
  })

  it.each(['success', 'failure'] as const)(
    'tracks only a cursor request as older-message loading until %s',
    async (outcome) => {
      const message = {
        id: 'current-message',
        sessionId: detail.session.id,
        role: 'learner' as const,
        content: 'Mensagem atual',
        createdAt: '2026-10-08T12:00:00Z',
        inReplyToMessageId: null,
      }
      const currentDetail = {
        ...detail,
        messages: { items: [message], nextCursor: 'older-page' },
      }
      mocks.detail.mockResolvedValue(currentDetail)
      const { result } = renderHook(() => useMentorContextProvider('aluna@example.com'), {
        wrapper: responseWrapper,
      })
      await waitFor(() => expect(result.current.isValidatingScope).toBe(false))
      await act(async () => result.current.selectSession(detail.session.id))
      expect(result.current.isReadingOlderMessages).toBe(false)
      let resolvePage!: (page: MentorSessionDetail) => void
      let rejectPage!: (error: Error) => void
      mocks.detail.mockImplementationOnce(
        () =>
          new Promise<MentorSessionDetail>((resolve, reject) => {
            resolvePage = resolve
            rejectPage = reject
          }),
      )
      let pending!: Promise<void>
      act(() => {
        pending = result.current.loadOlderMessages()
      })
      expect(result.current.isReadingMessages).toBe(true)
      expect(result.current.isReadingOlderMessages).toBe(true)
      expect(result.current.sessionDetail?.messages.items).toEqual([message])
      expect(mocks.detail).toHaveBeenLastCalledWith({
        data: {
          accountEmail: 'aluna@example.com',
          sessionId: detail.session.id,
          cursor: 'older-page',
        },
      })
      await act(async () => {
        if (outcome === 'failure') rejectPage(new Error('Page unavailable'))
        else resolvePage({ ...currentDetail, messages: { items: [], nextCursor: null } })
        await pending
      })
      expect(result.current.isReadingMessages).toBe(false)
      expect(result.current.isReadingOlderMessages).toBe(false)
      expect(result.current.sessionDetail?.messages.items).toEqual([message])
      if (outcome === 'failure')
        expect(result.current.conversationError).toContain('Não foi possível carregar')
    },
  )

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

class ControlledEventSource extends EventTarget {
  static instances: ControlledEventSource[] = []
  close = vi.fn()
  constructor(readonly url: string) {
    super()
    ControlledEventSource.instances.push(this)
  }
  emit(data: Record<string, unknown>) {
    this.dispatchEvent(
      new MessageEvent('mentor.response', { data: JSON.stringify(data) }),
    )
  }
}
const initialResponse: MentorResponseSnapshot = {
  attemptId: 'attempt-a',
  learnerMessageId: 'learner-a',
  status: 'processing',
  blocks: [],
  consultations: [],
  lastSequence: 0,
  failureCode: null,
}
function responseWrapper({ children }: { children: React.ReactNode }) {
  return createElement(
    QueryClientProvider,
    { client: new QueryClient({ defaultOptions: { mutations: { retry: false } } }) },
    children,
  )
}
function openResponseProvider(response: MentorResponseSnapshot = initialResponse) {
  vi.stubGlobal('EventSource', ControlledEventSource)
  ControlledEventSource.instances = []
  mocks.detail.mockResolvedValue({
    ...detail,
    pendingLearnerMessageId: 'learner-a',
    response,
  })
  return renderHook(() => useMentorContextProvider('aluna@example.com'), {
    wrapper: responseWrapper,
  })
}
function responseEvent(overrides: Record<string, unknown> = {}) {
  return {
    session_id: detail.session.id,
    attempt_id: 'attempt-a',
    sequence: 1,
    kind: 'block',
    status: 'processing',
    block: {
      block_key: 'block-a',
      ordinal: 0,
      intent: null,
      content: 'Texto aprovado completo',
    },
    consultation: null,
    failure_code: null,
    created_at: '2026-10-10T00:00:00Z',
    ...overrides,
  }
}
describe('useMentorContextProvider response lifecycle', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.list.mockResolvedValue(sessionsPage)
    mocks.location.pathname = '/intelligence'
  })
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })
  it.each(['failed', 'cancelled'] as const)(
    'discards streamed partial content and consultations on %s while preserving the learner for retry',
    async (status) => {
      const learnerMessage = {
        id: 'learner-a',
        sessionId: detail.session.id,
        role: 'learner' as const,
        content: '  Explique listas em Python.  ',
        createdAt: '2026-10-10T00:00:00Z',
        inReplyToMessageId: null,
      }
      const { result } = openResponseProvider()
      mocks.detail.mockResolvedValue({
        ...detail,
        messages: { items: [learnerMessage], nextCursor: null },
        pendingLearnerMessageId: learnerMessage.id,
        response: initialResponse,
      })
      await act(() => result.current.selectSession(detail.session.id))
      const source = getEventSource(0)
      act(() =>
        source.emit(
          responseEvent({
            kind: 'consultation',
            block: null,
            consultation: 'learning',
            progress: 'write-answer',
          }),
        ),
      )
      act(() => source.emit(responseEvent({ sequence: 2 })))
      expect(result.current.response?.blocks).toHaveLength(1)
      expect(result.current.response?.consultations).toEqual(['learning'])
      expect(result.current.shouldAnimateBlock('attempt-a', 'block-a')).toBe(true)
      act(() =>
        source.emit(
          responseEvent({
            sequence: 3,
            kind: status,
            status,
            block: null,
            failure_code: status === 'failed' ? 'technical-failure' : null,
          }),
        ),
      )
      expect(result.current.response?.status).toBe(status)
      expect(result.current.response?.blocks).toEqual([])
      expect(result.current.response?.consultations).toEqual([])
      expect(result.current.response?.progress).toBeNull()
      expect(result.current.shouldAnimateBlock('attempt-a', 'block-a')).toBe(false)
      expect(result.current.sessionDetail?.pendingLearnerMessageId).toBe(
        learnerMessage.id,
      )
      expect(result.current.sessionDetail?.messages.items).toEqual([learnerMessage])
      expect(source.close).toHaveBeenCalledOnce()
      mocks.retry.mockResolvedValue({
        ...initialResponse,
        attemptId: 'attempt-b',
        status: 'queued',
        lastSequence: 4,
      })
      await act(() => result.current.retryResponse())
      expect(result.current.response?.learnerMessageId).toBe(learnerMessage.id)
      expect(result.current.response?.attemptId).toBe('attempt-b')
      expect(result.current.sessionDetail?.messages.items).toEqual([learnerMessage])
      expect(mocks.create).not.toHaveBeenCalled()
      expect(mocks.submit).not.toHaveBeenCalled()
    },
  )
  it('replaces real workflow progress, preserves it through blocks and clears it on cancellation', async () => {
    const { result } = openResponseProvider()
    await act(() => result.current.selectSession(detail.session.id))
    const source = getEventSource(0)
    act(() =>
      source.emit(
        responseEvent({ kind: 'status', block: null, progress: 'write-answer' }),
      ),
    )
    expect(result.current.response?.progress).toBe('write-answer')
    act(() =>
      source.emit(
        responseEvent({
          sequence: 2,
          kind: 'status',
          block: null,
          progress: 'review-answer',
        }),
      ),
    )
    expect(result.current.response?.progress).toBe('review-answer')
    act(() =>
      source.emit(
        responseEvent({ kind: 'status', block: null, progress: 'write-answer' }),
      ),
    )
    expect(result.current.response?.progress).toBe('review-answer')
    act(() =>
      source.emit(
        responseEvent({
          sequence: 3,
          kind: 'status',
          block: null,
          progress: 'write-answer',
        }),
      ),
    )
    expect(result.current.response?.progress).toBe('write-answer')
    act(() => source.emit(responseEvent({ sequence: 4 })))
    expect(result.current.response?.progress).toBe('write-answer')
    act(() =>
      source.emit(
        responseEvent({
          sequence: 5,
          kind: 'cancelled',
          status: 'cancelled',
          block: null,
        }),
      ),
    )
    expect(result.current.response?.progress).toBeNull()
    expect(source.close).toHaveBeenCalledOnce()
  })
  it('orders independent approved blocks and preserves them through a newer partial detail snapshot', async () => {
    const { result } = openResponseProvider()
    await act(() => result.current.selectSession(detail.session.id))
    act(() => {
      getEventSource(0).emit(
        responseEvent({
          block: { block_key: 'later', ordinal: 1, intent: null, content: 'Segundo' },
        }),
      )
      getEventSource(0).emit(responseEvent({ sequence: 2 }))
    })
    expect(result.current.response?.blocks.map((block) => block.content)).toEqual([
      'Texto aprovado completo',
      'Segundo',
    ])
    mocks.detail.mockResolvedValue({
      ...detail,
      pendingLearnerMessageId: 'learner-a',
      response: {
        ...initialResponse,
        lastSequence: 3,
        blocks: [
          {
            blockKey: 'later',
            ordinal: 1,
            intent: null,
            content: 'Segundo',
            sources: [],
          },
        ],
      },
    })
    await act(() => result.current.refresh())
    expect(result.current.response?.blocks.map((block) => block.content)).toEqual([
      'Texto aprovado completo',
      'Segundo',
    ])
    expect(result.current.response?.lastSequence).toBe(3)
  })
  it('opens one stream, applies approved blocks once and fences old attempts and cleanup callbacks', async () => {
    const { result, rerender, unmount } = openResponseProvider()
    await act(() => result.current.selectSession(detail.session.id))
    expect(ControlledEventSource.instances).toHaveLength(1)
    const source = getEventSource(0)
    act(() => source.emit(responseEvent()))
    expect(result.current.response?.blocks.map((block) => block.content)).toEqual([
      'Texto aprovado completo',
    ])
    expect(result.current.shouldAnimateBlock('attempt-a', 'block-a')).toBe(true)
    act(() => {
      source.emit(responseEvent())
      source.emit(responseEvent({ sequence: 2, attempt_id: 'old-attempt' }))
    })
    expect(result.current.response?.lastSequence).toBe(1)
    rerender()
    expect(ControlledEventSource.instances).toHaveLength(1)
    act(() => result.current.markBlockPresented('attempt-a', 'block-a'))
    expect(result.current.shouldAnimateBlock('attempt-a', 'block-a')).toBe(false)
    unmount()
    expect(source.close).toHaveBeenCalledOnce()
    source.emit(responseEvent({ sequence: 3 }))
  })
  it('closes malformed input before serialized snapshot recovery and resumes at authoritative cursor', async () => {
    const { result } = openResponseProvider()
    await act(() => result.current.selectSession(detail.session.id))
    const source = getEventSource(0)
    mocks.detail.mockResolvedValue({
      ...detail,
      response: { ...initialResponse, lastSequence: 7 },
    })
    await act(async () => {
      source.dispatchEvent(new MessageEvent('mentor.response', { data: '<script>' }))
      source.dispatchEvent(new Event('error'))
    })
    expect(source.close).toHaveBeenCalledOnce()
    expect(ControlledEventSource.instances).toHaveLength(2)
    expect(getEventSource(1).url).toContain('after_sequence=7')
    act(() => source.emit(responseEvent({ sequence: 8 })))
    expect(result.current.response?.blocks).toEqual([])
  })
  it('cancels partial content and retries the same learner under a new attempt without resending', async () => {
    const { result } = openResponseProvider({
      ...initialResponse,
      blocks: [
        {
          blockKey: 'block-a',
          ordinal: 0,
          intent: null,
          content: 'Parcial',
          sources: [],
        },
      ],
    })
    await act(() => result.current.selectSession(detail.session.id))
    mocks.cancel.mockResolvedValue({
      ...initialResponse,
      status: 'cancelled',
      lastSequence: 2,
    })
    await act(() => result.current.cancelResponse())
    expect(result.current.response?.blocks).toEqual([])
    expect(result.current.sessionDetail?.pendingLearnerMessageId).toBe('learner-a')
    mocks.retry.mockResolvedValue({
      ...initialResponse,
      attemptId: 'attempt-b',
      status: 'queued',
      lastSequence: 3,
    })
    await act(() => result.current.retryResponse())
    expect(result.current.response?.attemptId).toBe('attempt-b')
    expect(result.current.response?.learnerMessageId).toBe('learner-a')
    expect(mocks.create).not.toHaveBeenCalled()
    expect(mocks.submit).not.toHaveBeenCalled()
  })
  it('keeps the current snapshot while an older message page returns a stale response', async () => {
    const current = {
      ...initialResponse,
      lastSequence: 5,
      blocks: [
        {
          blockKey: 'approved',
          ordinal: 0,
          intent: null,
          content: 'Resposta já aprovada',
          sources: [],
        },
      ],
    }
    const { result } = openResponseProvider(current)
    mocks.detail.mockResolvedValueOnce({
      ...detail,
      response: current,
      messages: { items: [], nextCursor: 'older-page' },
      pendingLearnerMessageId: 'learner-a',
    })
    await act(() => result.current.selectSession(detail.session.id))
    mocks.detail.mockResolvedValueOnce({
      ...detail,
      response: initialResponse,
      messages: {
        items: [
          {
            id: 'older-message',
            sessionId: detail.session.id,
            role: 'learner',
            content: 'Mensagem antiga',
            createdAt: '2026-10-09T00:00:00Z',
            inReplyToMessageId: null,
          },
        ],
        nextCursor: null,
      },
      pendingLearnerMessageId: 'learner-a',
    })
    await act(() => result.current.loadOlderMessages())
    expect(result.current.response?.lastSequence).toBe(5)
    expect(result.current.response?.blocks[0]?.content).toBe('Resposta já aprovada')
    expect(result.current.sessionDetail?.messages.items[0]?.content).toBe(
      'Mensagem antiga',
    )
  })
  it('does not regress a terminal event when refresh returns the same sequence with an active status', async () => {
    const { result } = openResponseProvider()
    await act(() => result.current.selectSession(detail.session.id))
    mocks.detail.mockResolvedValue({
      ...detail,
      response: { ...initialResponse, lastSequence: 1 },
      pendingLearnerMessageId: 'learner-a',
    })
    await act(async () =>
      getEventSource(0).emit(
        responseEvent({ kind: 'completed', status: 'completed', block: null }),
      ),
    )
    expect(result.current.response?.status).toBe('completed')
    expect(result.current.response?.lastSequence).toBe(1)
    expect(result.current.sessionDetail?.pendingLearnerMessageId).toBeNull()
    await act(() => result.current.refresh())
    expect(result.current.response?.status).toBe('completed')
    expect(ControlledEventSource.instances).toHaveLength(1)
  })
  it('ignores an older control snapshot after a newer approved event arrives', async () => {
    const { result } = openResponseProvider()
    await act(() => result.current.selectSession(detail.session.id))
    let resolveCancel: (snapshot: MentorResponseSnapshot) => void = () => undefined
    mocks.cancel.mockImplementation(
      () =>
        new Promise<MentorResponseSnapshot>((resolve) => {
          resolveCancel = resolve
        }),
    )
    let cancellation: Promise<void> | undefined
    act(() => {
      cancellation = result.current.cancelResponse()
    })
    act(() => getEventSource(0).emit(responseEvent({ sequence: 2 })))
    await act(async () => {
      resolveCancel({ ...initialResponse, status: 'cancelled', lastSequence: 1 })
      await cancellation
    })
    expect(result.current.response?.status).toBe('processing')
    expect(result.current.response?.lastSequence).toBe(2)
    expect(result.current.response?.blocks[0]?.content).toBe('Texto aprovado completo')
  })
  it('fences an in-flight reconciliation after cancel returns a terminal snapshot at the same sequence', async () => {
    const { result } = openResponseProvider()
    await act(() => result.current.selectSession(detail.session.id))
    let resolveDetail: (value: MentorSessionDetail) => void = () => undefined
    mocks.detail.mockImplementation(
      () =>
        new Promise<MentorSessionDetail>((resolve) => {
          resolveDetail = resolve
        }),
    )
    act(() => getEventSource(0).dispatchEvent(new Event('error')))
    mocks.cancel.mockResolvedValue({
      ...initialResponse,
      status: 'cancelled',
      lastSequence: 2,
    })
    await act(() => result.current.cancelResponse())
    await act(async () =>
      resolveDetail({
        ...detail,
        response: { ...initialResponse, lastSequence: 2 },
        pendingLearnerMessageId: 'learner-a',
      }),
    )
    expect(result.current.response?.status).toBe('cancelled')
    expect(result.current.response?.lastSequence).toBe(2)
    expect(result.current.response?.blocks).toEqual([])
    expect(ControlledEventSource.instances).toHaveLength(1)
  })
  it('captures a FAB hint on submit and keeps the idempotent retry hint after navigation', async () => {
    vi.stubGlobal('EventSource', ControlledEventSource)
    const hint = {
      goalId: 'goal-a',
      skillId: 'skill-a',
      competencyId: null,
      materialId: null,
      activityId: null,
    }
    const { result, rerender } = renderHook(
      ({ contextHint }) => useMentorContextProvider('aluna@example.com', contextHint),
      { wrapper: responseWrapper, initialProps: { contextHint: hint } },
    )
    mocks.detail.mockResolvedValue(detail)
    await act(() => result.current.selectSession(detail.session.id))
    act(() => result.current.setDraft('  Próxima pergunta  '))
    mocks.submit.mockRejectedValueOnce(new Error('Temporary network failure'))
    await act(() => result.current.sendFirstMessage('fab'))
    expect(result.current.draft).toBe('  Próxima pergunta  ')
    rerender({ contextHint: { ...hint, goalId: 'goal-b' } })
    mocks.submit.mockResolvedValue({
      ...detail,
      response: { ...initialResponse, status: 'queued' },
      pendingLearnerMessageId: 'learner-a',
    })
    await act(() => result.current.sendFirstMessage('fab'))
    expect(mocks.submit.mock.calls[0]?.[0]).toEqual(mocks.submit.mock.calls[1]?.[0])
    expect(mocks.submit.mock.calls[1]?.[0]).toEqual(
      expect.objectContaining({
        sessionId: detail.session.id,
        content: '  Próxima pergunta  ',
        contextHint: hint,
      }),
    )
    expect(result.current.draft).toBe('')
    expect(result.current.response?.status).toBe('queued')
  })
  it('clears private state when stream reconciliation loses account scope', async () => {
    const { result } = openResponseProvider()
    await act(() => result.current.selectSession(detail.session.id))
    mocks.detail.mockRejectedValue(new Error('Sua sessão expirou'))
    await act(async () => getEventSource(0).dispatchEvent(new Event('error')))
    expect(result.current.sessionDetail).toBeNull()
    expect(result.current.scopeError).toContain('Não foi possível confirmar')
    expect(ControlledEventSource.instances).toHaveLength(1)
  })
})

describe('useMentorContextProvider conversation summary', () => {
  const summaryState = {
    current: {
      version: 2,
      boundaryMessageId: 'message-boundary',
      coveredMessageCount: 21,
      completedAt: '2026-10-18T14:00:00Z',
      afterMessageId: null,
    },
    failureAfterMessageId: null,
  }
  const makeMessage = (id: string, createdAt: string) => ({
    id,
    sessionId: detail.session.id,
    role: 'learner' as const,
    content: `Mensagem ${id}`,
    inReplyToMessageId: null,
    createdAt,
    attachments: [],
  })
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.list.mockResolvedValue(sessionsPage)
    mocks.location.pathname = '/intelligence'
  })
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('exposes the empty summary state before a conversation is selected', () => {
    const { result } = openResponseProvider()

    expect(result.current.summary).toEqual({
      current: null,
      failureAfterMessageId: null,
    })
    expect(result.current.isSummarizingContext).toBe(false)
  })

  it('maps the summary state of the selected conversation detail', async () => {
    const { result } = openResponseProvider()
    mocks.detail.mockResolvedValue({
      ...detail,
      summary: summaryState,
      pendingLearnerMessageId: null,
      response: null,
    })

    await act(() => result.current.selectSession(detail.session.id))

    expect(result.current.summary).toEqual(summaryState)
  })

  it.each(['queued', 'processing'] as const)(
    'derives the summarizing state from a %s snapshot replayed with summarize-context progress',
    async (status) => {
      const { result } = openResponseProvider({
        ...initialResponse,
        status,
        progress: 'summarize-context',
      })

      await act(() => result.current.selectSession(detail.session.id))

      expect(result.current.isSummarizingContext).toBe(true)
    },
  )

  it('does not report summarizing once the response is no longer active', async () => {
    const { result } = openResponseProvider({
      ...initialResponse,
      status: 'completed',
      progress: 'summarize-context',
    })

    await act(() => result.current.selectSession(detail.session.id))

    expect(result.current.isSummarizingContext).toBe(false)
  })

  it('follows the live progress, keeps it through blocks and clears it on the closing null-progress status event', async () => {
    const { result } = openResponseProvider()
    await act(() => result.current.selectSession(detail.session.id))
    const source = getEventSource(0)

    act(() =>
      source.emit(
        responseEvent({ kind: 'status', block: null, progress: 'summarize-context' }),
      ),
    )
    expect(result.current.isSummarizingContext).toBe(true)
    expect(result.current.response?.progress).toBe('summarize-context')

    act(() =>
      source.emit(responseEvent({ sequence: 2, kind: 'consultation', block: null })),
    )
    expect(result.current.isSummarizingContext).toBe(true)

    act(() =>
      source.emit(
        responseEvent({ sequence: 3, kind: 'status', block: null, progress: null }),
      ),
    )
    expect(result.current.isSummarizingContext).toBe(false)
    expect(result.current.response?.progress).toBeNull()

    act(() =>
      source.emit(
        responseEvent({
          sequence: 4,
          kind: 'status',
          block: null,
          progress: 'write-answer',
        }),
      ),
    )
    expect(result.current.response?.progress).toBe('write-answer')
    expect(result.current.isSummarizingContext).toBe(false)
  })

  it('clears the summarizing state after reconnect when the snapshot replays the closing event', async () => {
    const { result } = openResponseProvider({
      ...initialResponse,
      lastSequence: 1,
      progress: 'summarize-context',
    })
    await act(() => result.current.selectSession(detail.session.id))
    expect(result.current.isSummarizingContext).toBe(true)
    const source = getEventSource(0)
    mocks.detail.mockResolvedValue({
      ...detail,
      pendingLearnerMessageId: 'learner-a',
      response: { ...initialResponse, lastSequence: 4, progress: null },
    })

    await act(async () => source.dispatchEvent(new Event('error')))

    expect(result.current.isSummarizingContext).toBe(false)
  })

  describe('revealMessage', () => {
    const newest = makeMessage('message-newest', '2026-10-08T12:03:00Z')
    const middle = makeMessage('message-middle', '2026-10-08T12:02:00Z')
    const oldest = makeMessage('message-oldest', '2026-10-08T12:01:00Z')
    const pages: Record<string, { items: (typeof newest)[]; nextCursor: string | null }> =
      {
        first: { items: [newest], nextCursor: 'page-2' },
        'page-2': { items: [middle], nextCursor: 'page-3' },
        'page-3': { items: [oldest], nextCursor: null },
      }
    function mockPages() {
      mocks.detail.mockImplementation(
        async ({ data }: { data: { cursor?: string } }) => ({
          ...detail,
          pendingLearnerMessageId: null,
          response: null,
          messages: pages[data.cursor ?? 'first'],
        }),
      )
    }

    it('returns true without reading when the message is already loaded', async () => {
      const { result } = openResponseProvider()
      mockPages()
      await act(() => result.current.selectSession(detail.session.id))
      mocks.detail.mockClear()

      let wasFound = false
      await act(async () => {
        wasFound = await result.current.revealMessage(newest.id)
      })

      expect(wasFound).toBe(true)
      expect(mocks.detail).not.toHaveBeenCalled()
    })

    it('pages older messages until the message is present', async () => {
      const { result } = openResponseProvider()
      mockPages()
      await act(() => result.current.selectSession(detail.session.id))
      mocks.detail.mockClear()

      let wasFound = false
      await act(async () => {
        wasFound = await result.current.revealMessage(oldest.id)
      })

      expect(wasFound).toBe(true)
      expect(mocks.detail.mock.calls.map(([call]) => call.data.cursor)).toEqual([
        'page-2',
        'page-3',
      ])
      expect(result.current.sessionDetail?.messages.items.map(({ id }) => id)).toEqual([
        oldest.id,
        middle.id,
        newest.id,
      ])
    })

    it('stops at the first page that contains the message', async () => {
      const { result } = openResponseProvider()
      mockPages()
      await act(() => result.current.selectSession(detail.session.id))
      mocks.detail.mockClear()

      let wasFound = false
      await act(async () => {
        wasFound = await result.current.revealMessage(middle.id)
      })

      expect(wasFound).toBe(true)
      expect(mocks.detail).toHaveBeenCalledTimes(1)
    })

    it('returns false when the message is absent from every page', async () => {
      const { result } = openResponseProvider()
      mockPages()
      await act(() => result.current.selectSession(detail.session.id))

      let wasFound = true
      await act(async () => {
        wasFound = await result.current.revealMessage('message-missing')
      })

      expect(wasFound).toBe(false)
      expect(result.current.sessionDetail?.messages.nextCursor).toBeNull()
    })

    function holdPage(cursor: string) {
      let release: () => void = () => undefined
      const gate = new Promise<void>((resolve) => {
        release = resolve
      })
      let isHeld = true
      mocks.detail.mockImplementation(async ({ data }: { data: { cursor?: string } }) => {
        if (data.cursor === cursor && isHeld) {
          isHeld = false
          await gate
        }
        return {
          ...detail,
          pendingLearnerMessageId: null,
          response: null,
          messages: pages[data.cursor ?? 'first'],
        }
      })
      return release
    }

    it('keeps revealing when an unrelated detail read overlaps a page read', async () => {
      const { result } = openResponseProvider()
      mockPages()
      await act(() => result.current.selectSession(detail.session.id))
      mocks.detail.mockClear()
      const release = holdPage('page-2')

      let reveal: Promise<boolean> = Promise.resolve(false)
      act(() => {
        reveal = result.current.revealMessage(oldest.id)
      })
      await act(async () => window.dispatchEvent(new Event('focus')))
      let wasFound = false
      await act(async () => {
        release()
        wasFound = await reveal
      })

      expect(wasFound).toBe(true)
      expect(result.current.sessionDetail?.messages.items.map(({ id }) => id)).toEqual([
        oldest.id,
        middle.id,
        newest.id,
      ])
    })

    it('aborts the reveal when the active conversation changes meanwhile', async () => {
      const { result } = openResponseProvider()
      mockPages()
      await act(() => result.current.selectSession(detail.session.id))
      mocks.detail.mockClear()
      const release = holdPage('page-2')

      let reveal: Promise<boolean> = Promise.resolve(true)
      act(() => {
        reveal = result.current.revealMessage(oldest.id)
      })
      await act(async () => result.current.startNewConversation())
      let wasFound = true
      await act(async () => {
        release()
        wasFound = await reveal
      })

      expect(wasFound).toBe(false)
      expect(result.current.sessionDetail).toBeNull()
    })

    it('gives up after bounded retries when the page never resolves', async () => {
      const { result } = openResponseProvider()
      mockPages()
      await act(() => result.current.selectSession(detail.session.id))
      mocks.detail.mockClear()
      mocks.detail.mockRejectedValue(new Error('indisponível'))

      let wasFound = true
      await act(async () => {
        wasFound = await result.current.revealMessage(oldest.id)
      })

      expect(wasFound).toBe(false)
      expect(mocks.detail).toHaveBeenCalledTimes(3)
    })

    it('returns false without a selected conversation and when a page read fails', async () => {
      const { result } = openResponseProvider()
      mockPages()
      let wasFound = true
      await act(async () => {
        wasFound = await result.current.revealMessage(oldest.id)
      })
      expect(wasFound).toBe(false)

      await act(() => result.current.selectSession(detail.session.id))
      mocks.detail.mockRejectedValue(new Error('indisponível'))
      await act(async () => {
        wasFound = await result.current.revealMessage(oldest.id)
      })
      expect(wasFound).toBe(false)
      expect(result.current.conversationError).toContain('Não foi possível carregar')
    })
  })
})

describe('useMentorContextProvider memory items', () => {
  const createdItem = LearnerMemoryFaker.fakeConversationItem({
    id: 'item-created',
    sourceMessageId: 'learner-a',
    kind: 'created',
    createdAt: '2026-10-10T00:00:02Z',
  })
  const olderItem = LearnerMemoryFaker.fakeConversationItem({
    id: 'item-older',
    sourceMessageId: 'learner-old',
    createdAt: '2026-10-10T00:00:01Z',
  })
  const learnerMessage = (id: string, createdAt: string) => ({
    id,
    sessionId: detail.session.id,
    role: 'learner' as const,
    content: `Mensagem ${id}`,
    inReplyToMessageId: null,
    createdAt,
    attachments: [],
  })
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.list.mockResolvedValue(sessionsPage)
    mocks.location.pathname = '/intelligence'
  })
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  function mockDetailWithItems(items: MentorSessionDetail['memoryItems']) {
    mocks.detail.mockResolvedValue({
      ...detail,
      pendingLearnerMessageId: 'learner-a',
      response: initialResponse,
      memoryItems: items,
    })
  }

  it('exposes the memory items of the selected conversation', async () => {
    const { result } = openResponseProvider()
    mockDetailWithItems([createdItem])

    await act(() => result.current.selectSession(detail.session.id))

    expect(result.current.sessionDetail?.memoryItems).toEqual([createdItem])
  })

  it.each([
    ['completed', 'completed'],
    ['failed', 'failed'],
    ['cancelled', 'cancelled'],
  ] as const)(
    're-reads the detail and shows the memory items when the response %s',
    async (kind, status) => {
      const { result } = openResponseProvider()
      await act(() => result.current.selectSession(detail.session.id))
      expect(result.current.sessionDetail?.memoryItems).toEqual([])
      mocks.detail.mockClear()
      mockDetailWithItems([createdItem])

      act(() =>
        getEventSource(0).emit(responseEvent({ sequence: 2, kind, status, block: null })),
      )

      await waitFor(() =>
        expect(result.current.sessionDetail?.memoryItems).toEqual([createdItem]),
      )
      expect(mocks.detail).toHaveBeenCalledTimes(1)
    },
  )

  it('refetches open learner memory queries when the response ends', async () => {
    const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
    const listMemories = vi.fn().mockResolvedValue([])
    const readMemory = vi.fn().mockResolvedValue(null)
    vi.stubGlobal('EventSource', ControlledEventSource)
    ControlledEventSource.instances = []
    mockDetailWithItems([])
    const { result } = renderHook(
      () => {
        useQuery({
          queryKey: ['learner-memories', 'aluna@example.com'],
          queryFn: listMemories,
        })
        useQuery({
          queryKey: ['learner-memory', 'aluna@example.com', 'm'],
          queryFn: readMemory,
        })
        return useMentorContextProvider('aluna@example.com')
      },
      {
        wrapper: ({ children }: { children: React.ReactNode }) =>
          createElement(QueryClientProvider, { client }, children),
      },
    )
    await act(() => result.current.selectSession(detail.session.id))
    await waitFor(() => expect(listMemories).toHaveBeenCalledTimes(1))
    expect(readMemory).toHaveBeenCalledTimes(1)

    act(() => getEventSource(0).emit(responseEvent({ sequence: 2, block: null })))
    expect(listMemories).toHaveBeenCalledTimes(1)
    act(() =>
      getEventSource(0).emit(
        responseEvent({
          sequence: 3,
          kind: 'completed',
          status: 'completed',
          block: null,
        }),
      ),
    )

    await waitFor(() => expect(listMemories).toHaveBeenCalledTimes(2))
    expect(readMemory).toHaveBeenCalledTimes(2)
  })

  it('does not re-read the detail for non-terminal events', async () => {
    const { result } = openResponseProvider()
    await act(() => result.current.selectSession(detail.session.id))
    mocks.detail.mockClear()

    act(() =>
      getEventSource(0).emit(
        responseEvent({
          sequence: 2,
          kind: 'consultation',
          block: null,
          consultation: 'learning',
        }),
      ),
    )
    act(() => getEventSource(0).emit(responseEvent({ sequence: 3 })))

    expect(mocks.detail).not.toHaveBeenCalled()
  })

  it('re-reads the detail after a user-initiated cancel, which never reaches the stream', async () => {
    const { result } = openResponseProvider()
    await act(() => result.current.selectSession(detail.session.id))
    mocks.detail.mockClear()
    mockDetailWithItems([createdItem])
    mocks.cancel.mockResolvedValue({
      ...initialResponse,
      status: 'cancelled',
      lastSequence: 2,
    })

    await act(() => result.current.cancelResponse())

    await waitFor(() =>
      expect(result.current.sessionDetail?.memoryItems).toEqual([createdItem]),
    )
    expect(mocks.detail).toHaveBeenCalledTimes(1)
    expect(result.current.response?.status).toBe('cancelled')
  })

  it('does not re-read the detail after a retry request', async () => {
    const { result } = openResponseProvider({ ...initialResponse, status: 'failed' })
    await act(() => result.current.selectSession(detail.session.id))
    mocks.detail.mockClear()
    mocks.retry.mockResolvedValue({
      ...initialResponse,
      attemptId: 'attempt-b',
      status: 'queued',
      lastSequence: 3,
    })

    await act(() => result.current.retryResponse())

    expect(mocks.detail).not.toHaveBeenCalled()
  })

  it('keeps known items when an older message page is read and adds the page items', async () => {
    const { result } = openResponseProvider()
    const newest = learnerMessage('learner-a', '2026-10-10T00:00:00Z')
    const oldest = learnerMessage('learner-old', '2026-10-09T00:00:00Z')
    mocks.detail.mockImplementation(async ({ data }: { data: { cursor?: string } }) =>
      data.cursor
        ? {
            ...detail,
            pendingLearnerMessageId: null,
            response: null,
            messages: { items: [oldest], nextCursor: null },
            memoryItems: [olderItem],
          }
        : {
            ...detail,
            pendingLearnerMessageId: null,
            response: null,
            messages: { items: [newest], nextCursor: 'older' },
            memoryItems: [createdItem],
          },
    )
    await act(() => result.current.selectSession(detail.session.id))

    await act(() => result.current.loadOlderMessages())

    expect(result.current.sessionDetail?.memoryItems).toEqual([olderItem, createdItem])
  })

  it('does not drop known items when an older page carries none', async () => {
    const { result } = openResponseProvider()
    mocks.detail.mockImplementation(async ({ data }: { data: { cursor?: string } }) => ({
      ...detail,
      pendingLearnerMessageId: null,
      response: null,
      messages: data.cursor
        ? {
            items: [learnerMessage('learner-old', '2026-10-09T00:00:00Z')],
            nextCursor: null,
          }
        : {
            items: [learnerMessage('learner-a', '2026-10-10T00:00:00Z')],
            nextCursor: 'older',
          },
      memoryItems: data.cursor ? [] : [createdItem],
    }))
    await act(() => result.current.selectSession(detail.session.id))

    await act(() => result.current.loadOlderMessages())

    expect(result.current.sessionDetail?.memoryItems).toEqual([createdItem])
  })

  it('replaces the items with the authoritative list of a full read', async () => {
    const { result } = openResponseProvider()
    mockDetailWithItems([createdItem])
    await act(() => result.current.selectSession(detail.session.id))
    const deleted = { ...createdItem, memoryId: null, content: null }
    mockDetailWithItems([deleted])

    act(() =>
      getEventSource(0).emit(
        responseEvent({
          sequence: 2,
          kind: 'completed',
          status: 'completed',
          block: null,
        }),
      ),
    )

    await waitFor(() =>
      expect(result.current.sessionDetail?.memoryItems).toEqual([deleted]),
    )
  })
})

describe('useMentorContextProvider action proposals', () => {
  const proposal: MentorActionProposal = {
    id: 'proposal-a',
    sourceMessageId: 'learner-a',
    kind: 'add_skill',
    skillId: 'skill-a',
    skillName: 'Funções em Python',
    goalId: 'goal-a',
    goalTitle: 'Aprender a programar',
    skillExperienceId: null,
    candidateGoals: [],
    justification: 'Você pediu ao Mentor para adicionar esta Habilidade.',
    status: 'pending',
    outcome: null,
    rejectionReason: null,
    resolvedGoalId: null,
    resolvedSkillExperienceId: null,
    createdAt: '2026-10-10T00:00:02Z',
  }
  const proposalDto = {
    id: 'proposal-a',
    source_message_id: 'learner-a',
    kind: 'add_skill',
    skill_id: 'skill-a',
    skill_name: 'Funções em Python',
    goal_id: 'goal-a',
    goal_title: 'Aprender a programar',
    skill_experience_id: null,
    candidate_goals: [],
    justification: 'Você pediu ao Mentor para adicionar esta Habilidade.',
    status: 'pending',
    outcome: null,
    rejection_reason: null,
    resolved_goal_id: null,
    resolved_skill_experience_id: null,
    created_at: '2026-10-10T00:00:02Z',
  }
  const finalProposal: MentorActionProposal = {
    ...proposal,
    status: 'completed',
    outcome: 'added',
    resolvedGoalId: 'goal-a',
  }
  const completedResponse: MentorResponseSnapshot = {
    ...initialResponse,
    status: 'completed',
    lastSequence: 3,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mocks.list.mockResolvedValue(sessionsPage)
    mocks.location.pathname = '/intelligence'
  })
  afterEach(() => {
    cleanup()
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  function mockDetail(
    actionItems: MentorActionProposal[],
    response: MentorResponseSnapshot | null = completedResponse,
  ) {
    mocks.detail.mockResolvedValue({
      ...detail,
      pendingLearnerMessageId: null,
      response,
      actionItems,
    })
  }

  async function openConversation(
    actionItems: MentorActionProposal[],
    response: MentorResponseSnapshot | null = completedResponse,
  ) {
    const view = openResponseProvider(response ?? completedResponse)
    mockDetail(actionItems, response)
    await act(() => view.result.current.selectSession(detail.session.id))
    return view
  }

  it('blocks the conversation on the first pending proposal and releases it when none is pending', async () => {
    const second = { ...proposal, id: 'proposal-b' }
    const { result } = await openConversation([finalProposal, proposal, second])

    expect(result.current.blockingActionProposalId).toBe('proposal-a')

    mockDetail([finalProposal, { ...second, status: 'declined' }])
    await act(() => result.current.refresh())

    expect(result.current.blockingActionProposalId).toBeNull()
  })

  it('has no blocking proposal without a conversation or without proposals', async () => {
    const { result } = await openConversation([])

    expect(result.current.blockingActionProposalId).toBeNull()
    expect(result.current.isRefreshingActions).toBe(false)
    expect(result.current.hasActionRefreshTimedOut).toBe(false)
  })

  it('refuses to send a message or start dictation while a proposal is pending', async () => {
    const { result } = await openConversation([proposal])
    act(() => result.current.setDraft('sim'))

    await act(() => result.current.sendFirstMessage())
    await act(() =>
      result.current.submitMessage({
        submissionKey: 'e9cfaab2-fb57-40e6-96aa-e6d7afdd7259',
        content: 'sim',
        contextHint: null,
      }),
    )

    expect(mocks.submit).not.toHaveBeenCalled()
    expect(mocks.create).not.toHaveBeenCalled()
    expect(result.current.canStartDictation).toBe(false)
  })

  it('adds a streamed action proposal to the detail and blocks the conversation', async () => {
    const { result } = openResponseProvider()
    mockDetail([], initialResponse)
    await act(() => result.current.selectSession(detail.session.id))

    act(() =>
      getEventSource(0).emit(
        responseEvent({
          sequence: 2,
          kind: 'action',
          block: null,
          action_proposal: proposalDto,
        }),
      ),
    )

    expect(result.current.sessionDetail?.actionItems).toEqual([proposal])
    expect(result.current.blockingActionProposalId).toBe('proposal-a')
  })

  it('keeps the detail state when a streamed proposal is already known', async () => {
    const { result } = openResponseProvider()
    mockDetail([finalProposal], initialResponse)
    await act(() => result.current.selectSession(detail.session.id))

    act(() =>
      getEventSource(0).emit(
        responseEvent({
          sequence: 2,
          kind: 'action',
          block: null,
          action_proposal: proposalDto,
        }),
      ),
    )

    expect(result.current.sessionDetail?.actionItems).toEqual([finalProposal])
    expect(result.current.blockingActionProposalId).toBeNull()
  })

  it('keeps a streamed proposal through a read that predates it while the answer runs', async () => {
    const { result } = openResponseProvider()
    mockDetail([], initialResponse)
    await act(() => result.current.selectSession(detail.session.id))
    act(() =>
      getEventSource(0).emit(
        responseEvent({
          sequence: 2,
          kind: 'action',
          block: null,
          action_proposal: proposalDto,
        }),
      ),
    )

    await act(() => result.current.refresh())

    expect(result.current.sessionDetail?.actionItems).toEqual([proposal])
  })

  it('replaces the proposals with the authoritative list of a read after the answer ended', async () => {
    const { result } = openResponseProvider()
    mockDetail([], initialResponse)
    await act(() => result.current.selectSession(detail.session.id))
    act(() =>
      getEventSource(0).emit(
        responseEvent({
          sequence: 2,
          kind: 'action',
          block: null,
          action_proposal: proposalDto,
        }),
      ),
    )
    mockDetail([])
    act(() =>
      getEventSource(0).emit(
        responseEvent({
          sequence: 3,
          kind: 'completed',
          status: 'completed',
          block: null,
        }),
      ),
    )

    await waitFor(() => expect(result.current.sessionDetail?.actionItems).toEqual([]))
    expect(result.current.blockingActionProposalId).toBeNull()
  })

  it('keeps the known proposals when an older message page carries other proposals', async () => {
    const olderProposal = {
      ...proposal,
      id: 'proposal-old',
      status: 'declined' as const,
      createdAt: '2026-10-09T00:00:00Z',
    }
    const { result } = openResponseProvider()
    mocks.detail.mockImplementation(async ({ data }: { data: { cursor?: string } }) => ({
      ...detail,
      pendingLearnerMessageId: null,
      response: completedResponse,
      messages: data.cursor
        ? { items: [], nextCursor: null }
        : { items: [], nextCursor: 'older' },
      actionItems: data.cursor ? [olderProposal] : [proposal],
    }))
    await act(() => result.current.selectSession(detail.session.id))

    await act(() => result.current.loadOlderMessages())

    expect(result.current.sessionDetail?.actionItems).toEqual([olderProposal, proposal])
  })

  describe('bounded refresh', () => {
    async function openBlocked() {
      const view = await openConversation([proposal])
      mocks.detail.mockClear()
      vi.useFakeTimers()
      return view
    }

    it('re-reads immediately and then every second until the proposal is final', async () => {
      const { result } = await openBlocked()
      mocks.detail
        .mockResolvedValueOnce({
          ...detail,
          response: completedResponse,
          actionItems: [proposal],
        })
        .mockResolvedValueOnce({
          ...detail,
          response: completedResponse,
          actionItems: [finalProposal],
        })

      await act(async () => result.current.onActionResolved('proposal-a'))

      expect(mocks.detail).toHaveBeenCalledTimes(1)
      expect(result.current.isRefreshingActions).toBe(true)
      expect(result.current.blockingActionProposalId).toBe('proposal-a')

      await act(async () => {
        await vi.advanceTimersByTimeAsync(999)
      })
      expect(mocks.detail).toHaveBeenCalledTimes(1)
      await act(async () => {
        await vi.advanceTimersByTimeAsync(1)
      })

      expect(mocks.detail).toHaveBeenCalledTimes(2)
      expect(result.current.isRefreshingActions).toBe(false)
      expect(result.current.hasActionRefreshTimedOut).toBe(false)
      expect(result.current.blockingActionProposalId).toBeNull()
      expect(result.current.sessionDetail?.actionItems).toEqual([finalProposal])
    })

    it('stops after one read when the proposal is already final', async () => {
      const { result } = await openBlocked()
      mockDetail([finalProposal])

      await act(async () => result.current.onActionResolved('proposal-a'))
      await act(async () => {
        await vi.advanceTimersByTimeAsync(5000)
      })

      expect(mocks.detail).toHaveBeenCalledTimes(1)
      expect(result.current.isRefreshingActions).toBe(false)
    })

    it('gives up after ten reads and lets the learner re-read with refreshActions', async () => {
      const { result } = await openBlocked()

      await act(async () => result.current.onActionResolved('proposal-a'))
      await act(async () => {
        await vi.advanceTimersByTimeAsync(20_000)
      })

      expect(mocks.detail).toHaveBeenCalledTimes(10)
      expect(result.current.isRefreshingActions).toBe(false)
      expect(result.current.hasActionRefreshTimedOut).toBe(true)
      expect(result.current.blockingActionProposalId).toBe('proposal-a')

      mocks.detail.mockClear()
      mockDetail([finalProposal])
      await act(async () => result.current.refreshActions())

      expect(mocks.detail).toHaveBeenCalledTimes(1)
      expect(result.current.hasActionRefreshTimedOut).toBe(false)
      expect(result.current.isRefreshingActions).toBe(false)
      expect(result.current.blockingActionProposalId).toBeNull()
    })

    it('counts a failed read as an attempt and keeps trying', async () => {
      const { result } = await openBlocked()
      mocks.detail.mockRejectedValueOnce(new Error('network')).mockResolvedValueOnce({
        ...detail,
        response: completedResponse,
        actionItems: [finalProposal],
      })

      await act(async () => result.current.onActionResolved('proposal-a'))
      expect(result.current.isRefreshingActions).toBe(true)
      expect(result.current.conversationError).toBeNull()
      await act(async () => {
        await vi.advanceTimersByTimeAsync(1000)
      })

      expect(result.current.blockingActionProposalId).toBeNull()
      expect(result.current.isRefreshingActions).toBe(false)
    })

    it('clears the private state when a read loses the account scope', async () => {
      const { result } = await openBlocked()
      mocks.detail.mockRejectedValueOnce(new Error('A sessão da conta mudou'))

      await act(async () => result.current.onActionResolved('proposal-a'))

      expect(result.current.scopeError).toBe(
        'Não foi possível confirmar sua sessão. Atualize a página.',
      )
      expect(result.current.sessionDetail).toBeNull()
      expect(result.current.isRefreshingActions).toBe(false)
    })

    it('abandons the refresh when another conversation is opened', async () => {
      const { result } = await openBlocked()

      await act(async () => result.current.onActionResolved('proposal-a'))
      expect(result.current.isRefreshingActions).toBe(true)
      act(() => result.current.startNewConversation())
      mocks.detail.mockClear()
      await act(async () => {
        await vi.advanceTimersByTimeAsync(20_000)
      })

      expect(mocks.detail).not.toHaveBeenCalled()
      expect(result.current.isRefreshingActions).toBe(false)
      expect(result.current.hasActionRefreshTimedOut).toBe(false)
    })

    it('does nothing without a selected conversation', async () => {
      const { result } = openResponseProvider()
      mocks.detail.mockClear()

      await act(async () => result.current.onActionResolved('proposal-a'))

      expect(mocks.detail).not.toHaveBeenCalled()
      expect(result.current.isRefreshingActions).toBe(false)
    })
  })
})

function getEventSource(index: number): ControlledEventSource {
  const source = ControlledEventSource.instances[index]
  if (!source) throw new Error('The expected consumer stream was not opened')
  return source
}
