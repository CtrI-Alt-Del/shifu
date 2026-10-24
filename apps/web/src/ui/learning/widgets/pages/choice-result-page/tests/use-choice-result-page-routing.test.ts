import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement, type ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { learningActivityPath, learningAttemptsPath } from '@/constants/routes'
import { RestResponse } from '@/core/shared/responses/rest-response'
import { useChoiceResultPage } from '../use-choice-result-page'

const mocks = vi.hoisted(() => ({
  getCurrentAccess: vi.fn(),
  get: vi.fn(),
  post: vi.fn(),
}))
vi.mock('@tanstack/react-start', () => ({
  createStart: () => ({}),
  createMiddleware: () => ({ server: (handler: unknown) => handler }),
  createServerFn: () => ({
    middleware: () => ({
      validator: (validate: (data: unknown) => unknown) => ({
        handler:
          (handler: (context: { data: unknown }) => Promise<unknown>) =>
          (context: { data: unknown }) =>
            handler({
              data: validate(context.data),
              context: { requestId: 'test-request-id' },
            } as never),
      }),
    }),
    validator: (validate: (data: unknown) => unknown) => ({
      handler:
        (handler: (context: { data: unknown }) => Promise<unknown>) =>
        (context: { data: unknown }) =>
          handler({
            data: validate(context.data),
            context: { requestId: 'test-request-id' },
          } as never),
    }),
  }),
}))
vi.mock('@tanstack/react-start/server', () => ({
  getRequest: () => new Request('http://shifu.test'),
}))
vi.mock('@/provision/auth/better-auth/better-auth-provider', () => ({
  getBetterAuthProvider: () => ({ getCurrentAccess: mocks.getCurrentAccess }),
}))
vi.mock('@/provision/auth/better-auth/better-auth-config', () => ({
  BetterAuthConfig: () => ({ identityURL: 'http://shifu.test' }),
}))
vi.mock('@/rest/axios/axios-rest-client', () => ({
  AxiosRestClient: () => ({ get: mocks.get, post: mocks.post }),
}))

const IDS = {
  goalId: '01J00000000000000000000001',
  skillId: '01J00000000000000000000002',
  competencyId: '01J00000000000000000000003',
  activityId: '01J00000000000000000000004',
  attemptId: '01J00000000000000000000005',
}
const ATTEMPT_PATH = `${learningAttemptsPath(IDS)}/${IDS.attemptId}`
const ACTIVITY_WIRE = {
  activity_id: IDS.activityId,
  title: 'Currículo atualizado',
  difficulty: 'easy',
  activity_revision: 'new-revision',
  can_submit: false,
  questions: [
    { key: 'choice', kind: 'single_choice', prompt: 'Nova questão', options: [] },
  ],
}

function attemptWire(status = 'completed', questions: readonly unknown[] = []) {
  return {
    attempt_id: IDS.attemptId,
    activity_id: IDS.activityId,
    status,
    submitted_at: '2026-10-20T12:00:00Z',
    retry_allowed: status === 'failed',
    failure_message: status === 'failed' ? 'Avaliação indisponível' : null,
    score: status === 'completed' ? 75 : null,
    progress_before: 20,
    progress_after: 50,
    status_before: 'in_progress',
    status_after: 'in_progress',
    next_action: {
      competency_id: IDS.competencyId,
      activity_id: '01J00000000000000000000006',
      difficulty: 'medium',
      type: 'reinforcement',
    },
    questions,
  }
}

function setup() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const props = {
    ...IDS,
    onOpenRecommendation: vi.fn(),
    onSessionExpired: vi.fn(),
  }
  const view = renderHook(() => useChoiceResultPage(props), {
    wrapper: ({ children }: { children: ReactNode }) =>
      createElement(QueryClientProvider, { client }, children),
  })
  return { ...view, client, props }
}

function respondWithAttempt(body: unknown, statusCode = 200) {
  mocks.get.mockImplementation(async (path: string) => {
    if (path === ATTEMPT_PATH) return new RestResponse({ statusCode, body })
    if (path === learningActivityPath(IDS))
      return new RestResponse({ statusCode: 200, body: ACTIVITY_WIRE })
    return new RestResponse({
      statusCode: 200,
      body: { availability: 'available', competencyId: IDS.competencyId },
    })
  })
}

describe('useChoiceResultPage routed result consumers', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.getCurrentAccess.mockResolvedValue({
      accountId: 'account-1',
      accessToken: 'test-token',
    })
    mocks.post.mockResolvedValue(new RestResponse({ statusCode: 200, body: {} }))
    respondWithAttempt(attemptWire())
  })
  afterEach(cleanup)

  it.each(['react', 'javascript_stdin'] as const)(
    'hydrates immutable %s files and rubric through the actual result consumer',
    async (kind) => {
      const submittedFiles = [
        { path: 'src/App.tsx', content: 'submitted source' },
        { path: 'src/components/Title.tsx', content: 'submitted additional source' },
      ]
      respondWithAttempt(
        attemptWire('completed', [
          {
            question_key: 'code',
            kind,
            prompt: 'Enunciado histórico',
            submitted_files: submittedFiles,
            score: 75,
            criterion_results: [
              {
                key: 'behavior',
                weight_percentage: 100,
                level: 75,
                comment_id: 'fixed-75',
                comment: 'Comentário histórico',
              },
            ],
            concept_observations: [
              { concept_id: 'concept-1', level: '75', observation_id: 'evidence-75' },
            ],
          },
          {
            question_key: 'choice',
            prompt: 'Escolha histórica',
            selected_option_keys: ['b'],
            score: 100,
            is_correct: true,
            explanation: 'Explicação histórica',
            disclosed_correct_option_keys: ['b'],
          },
        ]),
      )
      const { result } = setup()
      await waitFor(() => expect(result.current.pageState).toBe('result'))
      expect(result.current.attempt?.questions).toEqual([
        {
          key: 'code',
          kind,
          prompt: 'Enunciado histórico',
          score: 75,
          submittedFiles,
          criterionResults: [
            {
              key: 'behavior',
              weightPercentage: 100,
              level: 75,
              commentId: 'fixed-75',
              comment: 'Comentário histórico',
            },
          ],
          conceptObservations: [
            { conceptId: 'concept-1', level: '75', observationId: 'evidence-75' },
          ],
        },
        {
          key: 'choice',
          prompt: 'Escolha histórica',
          submittedOptionKeys: ['b'],
          score: 100,
          isCorrect: true,
          explanation: 'Explicação histórica',
          correctOptionKeys: ['b'],
        },
      ])
      expect(result.current.attempt?.nextAction).toEqual({
        competencyId: IDS.competencyId,
        activityId: '01J00000000000000000000006',
        difficulty: 'medium',
        type: 'reinforcement',
      })
      expect(result.current.canRetry).toBe(false)
      expect(mocks.get).toHaveBeenCalledWith(ATTEMPT_PATH, {
        headers: { Authorization: 'Bearer test-token' },
      })
      expect(result.current.renderProps.state).toBe('result')
      if (result.current.renderProps.state === 'result')
        expect(result.current.renderProps.activity.title).toBe('Currículo atualizado')
    },
  )

  it('keeps a pending attempt non-retryable when its question projection is absent', async () => {
    respondWithAttempt({
      ...attemptWire('pending'),
      next_action: null,
      questions: undefined,
    })
    const { result } = setup()
    await waitFor(() => expect(result.current.pageState).toBe('result'))
    expect(result.current.attempt).toMatchObject({ status: 'pending', nextAction: null })
    expect(result.current.attempt?.questions).toBeUndefined()
    await act(async () => result.current.handleRetryEvaluation())
    expect(mocks.post).not.toHaveBeenCalled()
  })

  it('retries a failed evaluation through HTTP and reloads the same attempt as pending', async () => {
    respondWithAttempt(attemptWire('failed'))
    const { result } = setup()
    await waitFor(() => expect(result.current.canRetry).toBe(true))
    mocks.post.mockImplementation(async () => {
      respondWithAttempt(attemptWire('pending'))
      return new RestResponse({ statusCode: 200, body: {} })
    })
    await act(async () => result.current.handleRetryEvaluation())
    await waitFor(() => expect(result.current.attempt?.status).toBe('pending'))
    expect(result.current.hasRetryError).toBe(false)
    expect(mocks.post).toHaveBeenCalledWith(
      `${ATTEMPT_PATH}/retry`,
      {},
      {
        headers: { Authorization: 'Bearer test-token' },
      },
    )
    expect(result.current.attempt?.attemptId).toBe(IDS.attemptId)
  })

  it('retains a retryable failure when the retry endpoint rejects the request', async () => {
    respondWithAttempt(attemptWire('failed'))
    mocks.post.mockResolvedValue(new RestResponse({ statusCode: 503 }))
    const { result } = setup()
    await waitFor(() => expect(result.current.canRetry).toBe(true))
    await act(async () => result.current.handleRetryEvaluation())
    expect(result.current.hasRetryError).toBe(true)
    expect(result.current.canRetry).toBe(true)
    expect(result.current.attempt?.status).toBe('failed')
  })

  it('fails closed when the stored answer discriminator is unsupported', async () => {
    respondWithAttempt(
      attemptWire('completed', [{ kind: 'python', question_key: 'unknown' }]),
    )
    const { result } = setup()
    await waitFor(() => expect(result.current.pageState).toBe('error'))
    expect(result.current.attempt).toBeNull()
    expect(result.current.renderProps.state).toBe('error')
  })

  it.each([404, 429, 503])(
    'preserves private absence or recovery for HTTP %s',
    async (statusCode) => {
      respondWithAttempt({}, statusCode)
      const { result } = setup()
      await waitFor(() =>
        expect(result.current.pageState).toBe(
          statusCode === 404 ? 'private-absence' : 'error',
        ),
      )
      expect(result.current.attempt).toBeNull()
      expect(result.current.hasRetryError).toBe(false)
    },
  )

  it('refreshes the pending attempt when the tab becomes visible again', async () => {
    respondWithAttempt(attemptWire('pending'))
    const { result } = setup()
    await waitFor(() => expect(result.current.pageState).toBe('result'))
    const attemptReadsBefore = mocks.get.mock.calls.filter(
      ([path]) => path === ATTEMPT_PATH,
    ).length

    document.dispatchEvent(new Event('visibilitychange'))

    await waitFor(() =>
      expect(
        mocks.get.mock.calls.filter(([path]) => path === ATTEMPT_PATH).length,
      ).toBeGreaterThan(attemptReadsBefore),
    )
  })

  it('reloads the activity and the attempt through the shared retry-load handler', async () => {
    const { result } = setup()
    await waitFor(() => expect(result.current.pageState).toBe('result'))
    mocks.get.mockClear()

    await act(async () => result.current.handleRetryLoad())

    expect(mocks.get).toHaveBeenCalledWith(ATTEMPT_PATH, expect.anything())
    expect(mocks.get).toHaveBeenCalledWith(learningActivityPath(IDS), expect.anything())
  })

  it('exposes an error-state retry that reloads the activity and the attempt', async () => {
    respondWithAttempt({}, 503)
    const { result } = setup()
    await waitFor(() => expect(result.current.pageState).toBe('error'))
    respondWithAttempt(attemptWire())
    mocks.get.mockClear()

    const { renderProps } = result.current
    if (renderProps.state !== 'error') throw new Error('unreachable')
    await act(async () => renderProps.onRetryLoad())

    await waitFor(() => expect(result.current.pageState).toBe('result'))
  })
})
