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

  it('maps a snake_case fill-in-the-blank attempt and fills the segment fields the API omits', async () => {
    respondWithAttempt(
      attemptWire('completed', [
        {
          question_key: 'fill-1',
          kind: 'fill_blanks',
          prompt: 'Complete o texto.',
          content_language: 'en',
          segments: [{ text: 'She ' }, { blank_key: 'b1' }, { text: '.' }],
          bank: [
            { key: 'w1', word: 'goes' },
            { key: 'w2', word: 'go' },
          ],
          placements: [{ blank_key: 'b1', word_key: 'w1' }],
          score: 100,
          is_correct: true,
          correct_blank_count: 1,
          blank_count: 1,
          explanation: 'Correto.',
          disclosed_expected_blanks: [{ blank_key: 'b1', accepted_words: ['goes'] }],
        },
      ]),
    )
    const { result } = setup()
    await waitFor(() => expect(result.current.pageState).toBe('result'))

    expect(result.current.attempt?.questions).toEqual([
      {
        key: 'fill-1',
        kind: 'fill_blanks',
        prompt: 'Complete o texto.',
        contentLanguage: 'en',
        segments: [
          { text: 'She ', blankKey: null },
          { text: null, blankKey: 'b1' },
          { text: '.', blankKey: null },
        ],
        bank: [
          { key: 'w1', word: 'goes' },
          { key: 'w2', word: 'go' },
        ],
        placements: [{ blankKey: 'b1', wordKey: 'w1' }],
        score: 100,
        isCorrect: true,
        correctBlankCount: 1,
        blankCount: 1,
        explanation: 'Correto.',
        expectedBlanks: [{ blankKey: 'b1', acceptedWords: ['goes'] }],
      },
    ])
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

  describe('practical preparation', () => {
    const practicalWire = {
      question_key: 'practice-1',
      kind: 'practical_preparation',
      prompt: 'Prepare legumes salteados.',
      records: [{ key: 'cuts', label: 'Cortes' }],
      photos: [{ record_key: 'cuts', photo_id: 'photo-1' }],
      reflection: null,
      criteria: [
        {
          key: 'cut',
          name: 'Corte',
          weight: '40',
          level: 75,
          comment: 'Quase uniforme.',
        },
        { key: 'heat', name: 'Calor', weight: 60, level: null, comment: null },
      ],
      closed_without_grade: false,
      unassessable_records: [],
      guidance: null,
    }

    it('maps the practical result with numeric weights, nullable levels and an empty reflection', async () => {
      respondWithAttempt(attemptWire('completed', [practicalWire]))
      const { result } = setup()
      await waitFor(() => expect(result.current.pageState).toBe('result'))

      expect(result.current.attempt?.questions).toEqual([
        {
          key: 'practice-1',
          kind: 'practical_preparation',
          prompt: 'Prepare legumes salteados.',
          records: [{ key: 'cuts', label: 'Cortes' }],
          photos: [{ recordKey: 'cuts', photoId: 'photo-1' }],
          reflection: '',
          score: null,
          criteria: [
            {
              key: 'cut',
              name: 'Corte',
              weight: 40,
              level: 75,
              comment: 'Quase uniforme.',
            },
            { key: 'heat', name: 'Calor', weight: 60, level: null, comment: null },
          ],
          closedWithoutGrade: false,
          unassessableRecords: [],
          guidance: null,
        },
      ])
    })

    it('maps omitted null fields of the wire result to null', async () => {
      const { reflection, guidance, ...omitted } = practicalWire
      void reflection
      void guidance
      respondWithAttempt(
        attemptWire('completed', [
          {
            ...omitted,
            criteria: [{ key: 'cut', name: 'Corte', weight: '40' }],
          },
        ]),
      )
      const { result } = setup()
      await waitFor(() => expect(result.current.pageState).toBe('result'))

      expect(result.current.attempt?.questions?.[0]).toMatchObject({
        reflection: '',
        guidance: null,
        criteria: [{ key: 'cut', weight: 40, level: null, comment: null }],
      })
    })

    it('exposes the Activity identity and an owner-only attempt photo URL for the page', async () => {
      respondWithAttempt(attemptWire('completed', [practicalWire]))
      const { result } = setup()
      await waitFor(() => expect(result.current.pageState).toBe('result'))

      const { renderProps } = result.current
      if (renderProps.state !== 'result') throw new Error('unreachable')
      expect(renderProps.detailIds).toEqual({
        goalId: IDS.goalId,
        skillId: IDS.skillId,
        competencyId: IDS.competencyId,
        activityId: IDS.activityId,
      })
      expect(renderProps.buildPracticePhotoUrl?.('photo-1')).toBe(
        `/api${learningAttemptsPath(IDS)}/${IDS.attemptId}/practice-photos/photo-1`,
      )
    })

    it('keeps polling after a retry until a review attempt completes without progress fields', async () => {
      const reviewCompleted = {
        ...attemptWire('completed', [{ ...practicalWire, score: '80' }]),
        score: null,
        progress_before: undefined,
        progress_after: undefined,
        status_before: undefined,
        status_after: undefined,
        next_action: undefined,
      }
      respondWithAttempt(attemptWire('failed'))
      const { result } = setup()
      await waitFor(() => expect(result.current.canRetry).toBe(true))
      // The server still answers 'failed' right after the retry, then completes.
      let reads = 0
      mocks.post.mockImplementation(async () => {
        mocks.get.mockImplementation(async (path: string) => {
          if (path === ATTEMPT_PATH) {
            reads += 1
            return new RestResponse({
              statusCode: 200,
              body: reads < 3 ? attemptWire('failed') : reviewCompleted,
            })
          }
          if (path === learningActivityPath(IDS))
            return new RestResponse({ statusCode: 200, body: ACTIVITY_WIRE })
          return new RestResponse({
            statusCode: 200,
            body: { availability: 'unavailable' },
          })
        })
        return new RestResponse({ statusCode: 200, body: {} })
      })

      await act(async () => result.current.handleRetryEvaluation())
      expect(result.current.attempt?.status).toBe('pending')
      expect(result.current.canRetry).toBe(false)
      await waitFor(() => expect(result.current.attempt?.status).toBe('completed'), {
        timeout: 12_000,
      })

      expect(result.current.attempt?.questions?.[0]).toMatchObject({
        score: 80,
        closedWithoutGrade: false,
      })
      expect(result.current.attempt?.score).toBeNull()
    }, 20_000)

    it('treats a closed attempt without grade as terminal and never retryable', async () => {
      respondWithAttempt({
        ...attemptWire('closed_without_grade', [
          {
            ...practicalWire,
            criteria: [],
            closed_without_grade: true,
            unassessable_records: [
              { key: 'cuts', label: 'Cortes', comment: 'Foto escura demais.' },
            ],
            guidance: 'Use mais luz.',
          },
        ]),
        score: null,
        progress_before: null,
        progress_after: null,
        next_action: null,
      })
      const { result } = setup()
      await waitFor(() => expect(result.current.pageState).toBe('result'))

      expect(result.current.attempt).toMatchObject({
        status: 'closed_without_grade',
        retryAllowed: false,
        score: null,
      })
      expect(result.current.attempt?.questions?.[0]).toMatchObject({
        closedWithoutGrade: true,
        unassessableRecords: [
          { key: 'cuts', label: 'Cortes', comment: 'Foto escura demais.' },
        ],
        guidance: 'Use mais luz.',
      })
      expect(result.current.canRetry).toBe(false)
    })
  })
})
