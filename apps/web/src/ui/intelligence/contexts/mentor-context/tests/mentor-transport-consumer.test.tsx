import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement, type PropsWithChildren } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { RestResponse } from '@/core/shared/responses/rest-response'
import { useMentorContextProvider } from '../use-mentor-context-provider'

const ports = vi.hoisted(() => ({
  post: vi.fn(),
  get: vi.fn(),
  access: vi.fn(),
  list: vi.fn(),
  navigate: vi.fn(),
}))
vi.mock('@tanstack/react-start', () => ({
  createServerFn: () => ({
    validator: (validate: (data: unknown) => unknown) => ({
      handler:
        (handle: (input: { data: unknown }) => unknown) => (input: { data: unknown }) =>
          handle({ data: validate(input.data) }),
    }),
  }),
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
  AxiosRestClient: () => ({ post: ports.post, get: ports.get }),
}))
vi.mock('@/ui/intelligence/hooks/mentor-server-functions', () => ({
  listMentorSessionsServer: ports.list,
  renameMentorSessionServer: vi.fn(),
  removeMentorSessionServer: vi.fn(),
}))
const sessionId = '01J7T8AC91Z5K8M4JQ8C2D6F0B'
const attemptId = '01J7T8AC91Z5K8M4JQ8C2D6F0C'
const submissionKey = 'e9cfaab2-fb57-40e6-96aa-e6d7afdd7259'
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
    ports.list.mockResolvedValue({ items: [], nextCursor: null })
    ports.get.mockResolvedValue(new RestResponse({ statusCode: 200, body: detail }))
    ports.post.mockImplementation(
      async (path: string) =>
        new RestResponse({
          statusCode: 202,
          body: path.endsWith('/cancel')
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
})
