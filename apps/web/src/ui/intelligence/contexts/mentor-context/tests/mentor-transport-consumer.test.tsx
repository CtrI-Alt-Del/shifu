import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement, type PropsWithChildren } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { RestResponse } from '@/core/shared/responses/rest-response'
import { getMentorSessionSummaryServer } from '@/ui/intelligence/widgets/components/mentor-chat/conversation/summary-marker/use-mentor-session-summary-query'
import { useMentorContextProvider } from '../use-mentor-context-provider'

const ports = vi.hoisted(() => ({
  post: vi.fn(),
  get: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
  access: vi.fn(),
  navigate: vi.fn(),
}))
vi.mock('@tanstack/react-start', () => ({
  createServerFn: () => ({
    middleware: () => ({
      validator: (validate: (data: unknown) => unknown) => ({
        handler:
          (handle: (input: { data: unknown }) => unknown) => (input: { data: unknown }) =>
            handle({ data: validate(input.data) }),
      }),
    }),
  }),
}))
vi.mock('@/start', () => ({
  serverFunctionTelemetryMiddleware: {},
}))
vi.mock('@tanstack/react-start/server', () => ({
  getRequest: () => new Request('http://localhost/mentor'),
}))
vi.mock('@tanstack/react-router', () => ({
  useLocation: () => ({ pathname: '/gamification', search: {} }),
  useNavigate: () => ports.navigate,
}))
vi.mock('@/provision/auth/better-auth/better-auth-provider', () => ({
  getBetterAuthProvider: () => ({ getCurrentAccess: ports.access }),
}))
vi.mock('@/rest/axios/axios-rest-client', () => ({
  AxiosRestClient: () => ({
    post: ports.post,
    get: ports.get,
    patch: ports.patch,
    delete: ports.delete,
    postFormData: vi.fn(),
    getFile: vi.fn(),
    put: vi.fn(),
  }),
}))
vi.mock('@/rest/fetch/fetch-rest-stream-client', () => ({
  FetchRestStreamClient: () => ({ getStream: vi.fn() }),
}))
const sessionId = '01J7T8AC91Z5K8M4JQ8C2D6F0B'
const attemptId = '01J7T8AC91Z5K8M4JQ8C2D6F0C'
const submissionKey = 'e9cfaab2-fb57-40e6-96aa-e6d7afdd7259'
const attachmentBatchId = '01J7T8AC91Z5K8M4JQ8C2D6F0E'
const attachmentId = '01J7T8AC91Z5K8M4JQ8C2D6F0F'
const attachmentDto = {
  attachment_id: attachmentId,
  filename: 'anotacao.txt',
  media_type: 'text/plain',
  size_bytes: 4,
  status: 'ready',
  failure_code: null,
  analyzed_pages: [],
  illegible_pages: [],
  uninterpreted_pages: [],
}
const attachmentDomain = {
  attachmentId,
  filename: 'anotacao.txt',
  mediaType: 'text/plain',
  sizeBytes: 4,
  status: 'processing',
  failureCode: null,
  analyzedPages: [],
  illegiblePages: [],
  uninterpretedPages: [],
}
const attachmentBatchDto = {
  batch_id: attachmentBatchId,
  expires_at: '2026-10-15T12:00:00Z',
  attachments: [attachmentDto],
}
const snapshot = {
  attempt_id: attemptId,
  learner_message_id: sessionId,
  status: 'processing',
  blocks: [
    { block_key: 'approved', ordinal: 0, intent: null, content: 'Resposta aprovada' },
  ],
  consultations: ['learning'],
  progress: 'review-answer',
  last_sequence: 2,
  failure_code: null,
}
const detail = {
  session: {
    id: sessionId,
    title: 'Dúvida',
    created_at: 'now',
    updated_at: 'now',
    last_activity_at: 'now',
  },
  messages: {
    items: [
      {
        id: sessionId,
        session_id: sessionId,
        role: 'learner',
        content: ' dúvida ',
        created_at: 'now',
        in_reply_to_message_id: null,
      },
    ],
    next_cursor: null,
  },
  pending_learner_message_id: sessionId,
  response: snapshot,
}
function wrapper({ children }: PropsWithChildren) {
  return createElement(
    QueryClientProvider,
    { client: new QueryClient({ defaultOptions: { mutations: { retry: false } } }) },
    children,
  )
}
describe('Mentor consumer through authenticated transport', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.stubGlobal(
      'EventSource',
      class {
        addEventListener() {}
        removeEventListener() {}
        close() {}
      },
    )
    ports.access.mockResolvedValue({
      email: 'learner@example.com',
      accessToken: 'test-access',
    })
    ports.get.mockImplementation(async (path: string) => {
      if (path === '/intelligence/mentor-sessions')
        return new RestResponse({
          statusCode: 200,
          body: { items: [], next_cursor: null },
        })
      if (path.includes('/mentor-attachment-batches/'))
        return new RestResponse({ statusCode: 200, body: attachmentBatchDto })
      return new RestResponse({ statusCode: 200, body: detail })
    })
    ports.post.mockImplementation(
      async (path: string) =>
        new RestResponse({
          statusCode: path.includes('/mentor-attachment-batches') ? 201 : 202,
          body:
            path === '/intelligence/mentor-attachment-batches'
              ? {
                  batch_id: attachmentBatchId,
                  expires_at: attachmentBatchDto.expires_at,
                }
              : path.endsWith('/cancel')
                ? { ...snapshot, status: 'cancelled', blocks: [], last_sequence: 3 }
                : path.endsWith('/retry')
                  ? {
                      ...snapshot,
                      status: 'queued',
                      attempt_id: '01J7T8AC91Z5K8M4JQ8C2D6F0D',
                      blocks: [],
                      last_sequence: 4,
                    }
                  : detail,
        }),
    )
    ports.patch.mockResolvedValue(
      new RestResponse({
        statusCode: 200,
        body: {
          id: sessionId,
          title: 'Título atualizado',
          created_at: 'now',
          updated_at: 'now',
          last_activity_at: 'now',
        },
      }),
    )
    ports.delete.mockResolvedValue(new RestResponse({ statusCode: 204 }))
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response(JSON.stringify(attachmentDomain), {
            status: 201,
            headers: { 'Content-Type': 'application/json' },
          }),
      ),
    )
  })
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })
  it.each([false, true])(
    'creates exact learner text with Learning hint %s and retries without a new hint',
    async (hasHint) => {
      const hint = hasHint
        ? {
            goalId: sessionId,
            skillId: attemptId,
            competencyId: null,
            materialId: null,
            activityId: null,
          }
        : null
      const { result } = renderHook(
        () => useMentorContextProvider('learner@example.com', hint),
        { wrapper },
      )
      await waitFor(() => expect(result.current.isValidatingScope).toBe(false))
      act(() => result.current.setDraft(' dúvida '))
      await act(() => result.current.sendFirstMessage(hasHint ? 'fab' : 'page'))
      expect(ports.post).toHaveBeenCalledWith(
        '/intelligence/mentor-sessions',
        {
          submission_key: expect.any(String),
          first_message: ' dúvida ',
          ...(hasHint
            ? {
                context_hint: {
                  goal_id: sessionId,
                  skill_id: attemptId,
                  competency_id: null,
                  material_id: null,
                  activity_id: null,
                },
              }
            : {}),
        },
        {
          headers: { Authorization: 'Bearer test-access', 'Cache-Control': 'no-store' },
        },
      )
      if (!hasHint)
        expect(ports.post.mock.calls[0]?.[1]).not.toHaveProperty('context_hint')
      expect(result.current.response?.blocks[0]?.content).toBe('Resposta aprovada')
      await act(() => result.current.cancelResponse())
      expect(result.current.response?.status).toBe('cancelled')
      await act(() => result.current.retryResponse())
      expect(result.current.response?.status).toBe('queued')
      expect(ports.post.mock.calls.at(-1)?.[1]).toEqual({
        submission_key: expect.any(String),
      })
    },
  )
  it('submits captured Learning context and reconciles authenticated detail', async () => {
    const hint = {
      goalId: sessionId,
      skillId: null,
      competencyId: null,
      materialId: null,
      activityId: null,
    }
    ports.get.mockResolvedValue(
      new RestResponse({
        statusCode: 200,
        body: { ...detail, pending_learner_message_id: null, response: null },
      }),
    )
    const { result } = renderHook(
      () => useMentorContextProvider('learner@example.com', hint),
      { wrapper },
    )
    await waitFor(() => expect(result.current.isValidatingScope).toBe(false))
    await act(() => result.current.selectSession(sessionId))
    await act(() =>
      result.current.submitMessage({
        submissionKey,
        content: ' dúvida ',
        contextHint: hint,
      }),
    )
    expect(ports.post).toHaveBeenCalledWith(
      `/intelligence/mentor-sessions/${sessionId}/messages`,
      {
        submission_key: submissionKey,
        content: ' dúvida ',
        context_hint: {
          goal_id: sessionId,
          skill_id: null,
          competency_id: null,
          material_id: null,
          activity_id: null,
        },
      },
      expect.any(Object),
    )
    expect(result.current.response?.lastSequence).toBe(2)
    expect(result.current.response?.progress).toBe('review-answer')
    await act(() => result.current.refresh())
    expect(ports.get).toHaveBeenCalledWith(
      `/intelligence/mentor-sessions/${sessionId}`,
      expect.objectContaining({ params: { cursor: undefined } }),
    )
  })
  it('keeps a failed send retryable and rejects a changed authenticated account before posting', async () => {
    const { result } = renderHook(() => useMentorContextProvider('learner@example.com'), {
      wrapper,
    })
    await waitFor(() => expect(result.current.isValidatingScope).toBe(false))
    act(() => result.current.setDraft(' dúvida '))
    ports.post.mockResolvedValue(new RestResponse({ statusCode: 503 }))
    await act(() => result.current.sendFirstMessage())
    expect(result.current.submissionError).toBeTruthy()
    expect(result.current.draft).toBe(' dúvida ')
    ports.access.mockResolvedValue({
      email: 'different@example.com',
      accessToken: 'foreign',
    })
    await act(() => result.current.sendFirstMessage())
    expect(result.current.scopeError).toBeTruthy()
    expect(ports.post).toHaveBeenCalledTimes(1)
  })
  it.each([
    { surface: 'page' as const, existingSession: false, status: 'ready', draft: '' },
    { surface: 'fab' as const, existingSession: false, status: 'partial', draft: '   ' },
    { surface: 'page' as const, existingSession: true, status: 'partial', draft: '' },
    { surface: 'fab' as const, existingSession: true, status: 'ready', draft: '   ' },
  ])(
    'sends attachment-only text on $surface (existing=$existingSession, $status) and replays a failed send',
    async ({ surface, existingSession, status, draft }) => {
      ports.get.mockImplementation(async (path: string) => {
        if (path === '/intelligence/mentor-sessions')
          return new RestResponse({
            statusCode: 200,
            body: { items: [], next_cursor: null },
          })
        if (path.includes('/mentor-attachment-batches/'))
          return new RestResponse({
            statusCode: 200,
            body: { ...attachmentBatchDto, attachments: [{ ...attachmentDto, status }] },
          })
        return new RestResponse({
          statusCode: 200,
          body: { ...detail, pending_learner_message_id: null, response: null },
        })
      })
      const { result } = renderHook(
        () => useMentorContextProvider('learner@example.com'),
        { wrapper },
      )
      await waitFor(() => expect(result.current.isValidatingScope).toBe(false))
      if (existingSession) await act(() => result.current.selectSession(sessionId))
      act(() => result.current.setDraft(draft))
      await act(() =>
        result.current.addAttachments([
          new File(['nota'], 'anotacao.txt', { type: 'text/plain' }),
        ]),
      )
      await waitFor(() =>
        expect(result.current.draftAttachments[0]?.attachment?.status).toBe(status),
      )
      const endpoint = existingSession
        ? `/intelligence/mentor-sessions/${sessionId}/messages`
        : '/intelligence/mentor-sessions'
      ports.post.mockResolvedValueOnce(new RestResponse({ statusCode: 503 }))
      await act(() => result.current.sendFirstMessage(surface))
      expect(result.current.submissionError).toBe(
        'Não foi possível enviar sua mensagem. Tente novamente.',
      )
      expect(result.current.draft).toBe(draft)
      expect(result.current.draftAttachments[0]?.attachment?.attachmentId).toBe(
        attachmentId,
      )
      await act(() => result.current.sendFirstMessage(surface))
      const submissions = ports.post.mock.calls.filter(([path]) => path === endpoint)
      expect(submissions).toHaveLength(2)
      expect(submissions[0]?.[1]).toEqual(submissions[1]?.[1])
      expect(submissions[1]?.[1]).toEqual(
        expect.objectContaining({
          [existingSession ? 'content' : 'first_message']: '',
          attachment_batch_id: attachmentBatchId,
          attachment_ids: [attachmentId],
          submission_key: expect.any(String),
        }),
      )
      expect(result.current.draftAttachments).toEqual([])
      expect(result.current.selectedSessionId).toBe(sessionId)
    },
  )

  it.each(['', '   '])(
    'blocks a completely empty submission with draft %j before posting',
    async (draft) => {
      const { result } = renderHook(
        () => useMentorContextProvider('learner@example.com'),
        { wrapper },
      )
      await waitFor(() => expect(result.current.isValidatingScope).toBe(false))
      act(() => result.current.setDraft(draft))
      await act(() => result.current.sendFirstMessage())
      expect(ports.post).not.toHaveBeenCalled()
    },
  )

  it.each([
    {},
    { attachmentIds: [] },
    { attachmentIds: [attachmentId] },
    { attachmentBatchId, attachmentIds: ['invalid-id'] },
  ])(
    'rejects blank direct continuation input with invalid selection %j',
    async (selection) => {
      ports.get.mockImplementation(
        async (path: string) =>
          new RestResponse({
            statusCode: 200,
            body:
              path === '/intelligence/mentor-sessions'
                ? { items: [], next_cursor: null }
                : { ...detail, pending_learner_message_id: null, response: null },
          }),
      )
      const { result } = renderHook(
        () => useMentorContextProvider('learner@example.com'),
        { wrapper },
      )
      await waitFor(() => expect(result.current.isValidatingScope).toBe(false))
      await act(() => result.current.selectSession(sessionId))
      await act(() =>
        result.current.submitMessage({
          submissionKey,
          content: '',
          contextHint: null,
          ...selection,
        }),
      )
      expect(ports.post).not.toHaveBeenCalled()
      expect(result.current.submissionError).toBe(
        'Não foi possível enviar sua mensagem. Tente novamente.',
      )
    },
  )

  it.each(['processing', 'failed'])(
    'blocks attachment-only sending when an attachment is %s',
    async (status) => {
      vi.stubGlobal(
        'fetch',
        vi.fn(
          async () =>
            new Response(JSON.stringify({ ...attachmentDomain, status }), {
              status: 201,
              headers: { 'Content-Type': 'application/json' },
            }),
        ),
      )
      ports.get.mockImplementation(
        async (path: string) =>
          new RestResponse({
            statusCode: 200,
            body: path.includes('/mentor-attachment-batches/')
              ? { ...attachmentBatchDto, attachments: [{ ...attachmentDto, status }] }
              : { items: [], next_cursor: null },
          }),
      )
      const { result } = renderHook(
        () => useMentorContextProvider('learner@example.com'),
        { wrapper },
      )
      await waitFor(() => expect(result.current.isValidatingScope).toBe(false))
      await act(() =>
        result.current.addAttachments([
          new File(['nota'], 'anotacao.txt', { type: 'text/plain' }),
        ]),
      )
      await act(() => result.current.sendFirstMessage())
      expect(ports.post.mock.calls.map(([path]) => path)).toEqual([
        '/intelligence/mentor-attachment-batches',
      ])
      expect(result.current.draftAttachments).toHaveLength(1)
    },
  )

  it('runs attachment creation, upload, polling, and removal through provider actions', async () => {
    const { result } = renderHook(() => useMentorContextProvider('learner@example.com'), {
      wrapper,
    })
    await waitFor(() => expect(result.current.isValidatingScope).toBe(false))

    await act(() =>
      result.current.addAttachments([
        new File(['nota'], 'anotacao.txt', { type: 'text/plain' }),
      ]),
    )
    await waitFor(() =>
      expect(result.current.draftAttachments[0]?.attachment?.status).toBe('ready'),
    )
    expect(ports.get).toHaveBeenCalledWith(
      `/intelligence/mentor-attachment-batches/${attachmentBatchId}`,
      expect.any(Object),
    )
    expect(ports.post).toHaveBeenCalledWith(
      '/intelligence/mentor-attachment-batches',
      {},
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: 'Bearer test-access' }),
      }),
    )
    expect(fetch).toHaveBeenCalledWith(
      `/api/intelligence/mentor-attachment-batches/${attachmentBatchId}/attachments`,
      expect.objectContaining({ method: 'POST' }),
    )

    const draftAttachment = result.current.draftAttachments[0]
    expect(draftAttachment?.attachment?.attachmentId).toBe(attachmentId)
    if (!draftAttachment) throw new Error('Expected uploaded draft attachment')
    await act(() => result.current.removeAttachment(draftAttachment.localKey))
    expect(ports.delete).toHaveBeenCalledWith(
      `/intelligence/mentor-attachment-batches/${attachmentBatchId}/attachments/${attachmentId}`,
      undefined,
      expect.any(Object),
    )
  })
  it('routes session rename and removal through their operation-owned server functions', async () => {
    const { result } = renderHook(() => useMentorContextProvider('learner@example.com'), {
      wrapper,
    })
    await waitFor(() => expect(result.current.isValidatingScope).toBe(false))
    act(() => result.current.openRenameDialog(sessionId))
    await act(() => result.current.renameSession('Título atualizado'))
    expect(ports.patch).toHaveBeenCalledWith(
      `/intelligence/mentor-sessions/${sessionId}`,
      { title: 'Título atualizado' },
      expect.any(Object),
    )
    act(() => result.current.openRemoveDialog(sessionId))
    await act(() => result.current.removeSession())
    expect(ports.delete).toHaveBeenCalledWith(
      `/intelligence/mentor-sessions/${sessionId}`,
      undefined,
      expect.any(Object),
    )
  })
  it('creates an attachment batch scoped to the selected session', async () => {
    const { result } = renderHook(() => useMentorContextProvider('learner@example.com'), {
      wrapper,
    })
    await waitFor(() => expect(result.current.isValidatingScope).toBe(false))
    await act(() => result.current.selectSession(sessionId))
    await act(() =>
      result.current.addAttachments([
        new File(['nota'], 'anotacao.txt', { type: 'text/plain' }),
      ]),
    )
    await waitFor(() =>
      expect(result.current.draftAttachments[0]?.attachment?.status).toBe('ready'),
    )
    expect(ports.post).toHaveBeenCalledWith(
      '/intelligence/mentor-attachment-batches',
      { session_id: sessionId },
      expect.any(Object),
    )
  })
  it.each([
    {
      code: 'attachment_too_large',
      message: 'Não foi possível enviar o arquivo. Tente novamente ou remova-o.',
    },
    {
      code: 'backend_error',
      message: 'Não foi possível enviar o arquivo. Tente novamente ou remova-o.',
    },
    {
      code: null,
      message: 'Não foi possível enviar o arquivo. Tente novamente ou remova-o.',
    },
  ])('shows the upload failure message for code $code', async ({ code, message }) => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          ({
            ok: false,
            json: async () => {
              if (code === null) throw new Error('invalid response')
              return { code }
            },
          }) as Response,
      ),
    )
    const { result } = renderHook(() => useMentorContextProvider('learner@example.com'), {
      wrapper,
    })
    await waitFor(() => expect(result.current.isValidatingScope).toBe(false))
    await act(() =>
      result.current.addAttachments([
        new File(['nota'], 'anotacao.txt', { type: 'text/plain' }),
      ]),
    )
    await waitFor(() => expect(result.current.draftAttachments[0]?.error).toBe(message))
  })
  it.each(['submit', 'cancel', 'retry'] as const)(
    'preserves authoritative response when %s transport fails',
    async (operation) => {
      const status =
        operation === 'submit'
          ? 'completed'
          : operation === 'retry'
            ? 'failed'
            : 'processing'
      const initial = {
        ...detail,
        pending_learner_message_id: status === 'completed' ? null : sessionId,
        response: { ...snapshot, status },
      }
      ports.get.mockResolvedValue(new RestResponse({ statusCode: 200, body: initial }))
      const { result } = renderHook(
        () => useMentorContextProvider('learner@example.com'),
        { wrapper },
      )
      await waitFor(() => expect(result.current.isValidatingScope).toBe(false))
      await act(() => result.current.selectSession(sessionId))
      ports.post.mockResolvedValue(new RestResponse({ statusCode: 503 }))
      await act(async () => {
        if (operation === 'submit')
          await result.current.submitMessage({
            submissionKey,
            content: ' dúvida ',
            contextHint: null,
          })
        else if (operation === 'cancel') await result.current.cancelResponse()
        else await result.current.retryResponse()
      })
      expect(result.current.response?.status).toBe(status)
      expect(
        result.current.conversationError ?? result.current.submissionError,
      ).toBeTruthy()
    },
  )
  describe('conversation summary', () => {
    const boundaryMessageId = '01J7T8AC91Z5K8M4JQ8C2D6F0G'
    const summaryDetail = {
      ...detail,
      summary: {
        current: {
          version: 2,
          boundary_message_id: boundaryMessageId,
          covered_message_count: 21,
          completed_at: '2026-10-18T14:00:00Z',
          after_message_id: '01J7T8AC91Z5K8M4JQ8C2D6F0H',
        },
        failure_after_message_id: sessionId,
      },
    }
    class ControlledEventSource extends EventTarget {
      static instances: ControlledEventSource[] = []
      close = vi.fn()
      constructor() {
        super()
        ControlledEventSource.instances.push(this)
      }
      emit(data: Record<string, unknown>) {
        this.dispatchEvent(
          new MessageEvent('mentor.response', { data: JSON.stringify(data) }),
        )
      }
    }
    const statusEvent = (sequence: number, progress: string | null) => ({
      session_id: sessionId,
      attempt_id: attemptId,
      sequence,
      kind: 'status',
      status: 'processing',
      block: null,
      consultation: null,
      progress,
      failure_code: null,
      created_at: '2026-10-18T14:00:00Z',
    })

    it('maps the authenticated detail summary and a replayed summarize-context snapshot', async () => {
      ports.get.mockResolvedValue(
        new RestResponse({
          statusCode: 200,
          body: {
            ...summaryDetail,
            response: { ...snapshot, blocks: [], progress: 'summarize-context' },
          },
        }),
      )
      const { result } = renderHook(
        () => useMentorContextProvider('learner@example.com'),
        { wrapper },
      )
      await waitFor(() => expect(result.current.isValidatingScope).toBe(false))
      await act(() => result.current.selectSession(sessionId))

      expect(result.current.summary).toEqual({
        current: {
          version: 2,
          boundaryMessageId,
          coveredMessageCount: 21,
          completedAt: '2026-10-18T14:00:00Z',
          afterMessageId: '01J7T8AC91Z5K8M4JQ8C2D6F0H',
        },
        failureAfterMessageId: sessionId,
      })
      expect(result.current.response?.progress).toBe('summarize-context')
      expect(result.current.isSummarizingContext).toBe(true)
    })

    it('keeps an empty summary when the detail carries none', async () => {
      const { result } = renderHook(
        () => useMentorContextProvider('learner@example.com'),
        { wrapper },
      )
      await waitFor(() => expect(result.current.isValidatingScope).toBe(false))
      await act(() => result.current.selectSession(sessionId))

      expect(result.current.summary).toEqual({
        current: null,
        failureAfterMessageId: null,
      })
      expect(result.current.isSummarizingContext).toBe(false)
    })

    it('accepts summarize-context and the closing null progress from the response stream', async () => {
      ControlledEventSource.instances = []
      vi.stubGlobal('EventSource', ControlledEventSource)
      ports.get.mockResolvedValue(
        new RestResponse({
          statusCode: 200,
          body: { ...detail, response: { ...snapshot, blocks: [], progress: null } },
        }),
      )
      const { result } = renderHook(
        () => useMentorContextProvider('learner@example.com'),
        { wrapper },
      )
      await waitFor(() => expect(result.current.isValidatingScope).toBe(false))
      await act(() => result.current.selectSession(sessionId))
      const source = ControlledEventSource.instances[0]
      if (!source) throw new Error('The response stream was not opened')

      act(() => source.emit(statusEvent(3, 'summarize-context')))
      expect(result.current.isSummarizingContext).toBe(true)
      expect(ControlledEventSource.instances).toHaveLength(1)

      act(() => source.emit(statusEvent(4, null)))
      expect(result.current.isSummarizingContext).toBe(false)
      expect(result.current.response?.progress).toBeNull()
      expect(ControlledEventSource.instances).toHaveLength(1)
    })

    it('reads the summary content through an authenticated GET server function', async () => {
      ports.get.mockResolvedValue(
        new RestResponse({
          statusCode: 200,
          body: {
            version: 2,
            text: 'Nesta conversa, os assuntos foram range.',
            covered_message_count: 21,
            first_message_id: boundaryMessageId,
          },
        }),
      )

      const content = await getMentorSessionSummaryServer({ data: { sessionId } })

      expect(ports.get).toHaveBeenCalledWith(
        `/intelligence/mentor-sessions/${sessionId}/summary`,
        {
          headers: { Authorization: 'Bearer test-access', 'Cache-Control': 'no-store' },
        },
      )
      expect(content).toEqual({
        version: 2,
        text: 'Nesta conversa, os assuntos foram range.',
        coveredMessageCount: 21,
        firstMessageId: boundaryMessageId,
      })
    })
  })
})
