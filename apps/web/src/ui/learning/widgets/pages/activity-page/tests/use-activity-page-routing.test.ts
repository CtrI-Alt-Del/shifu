import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement, type ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { RestResponse } from '@/core/shared/responses/rest-response'
import { learningActivityPath } from '@/constants/routes'
import { useActivityPage, type ActivityRouteProps } from '../use-activity-page'
import type { DiagnosticOverview } from '@/core/learning/goal-detail'
import { AuthError } from '@/core/errors/auth-error'
import {
  clearDiagnosticRun,
  getDiagnosticRun,
  setDiagnosticRun,
} from '@/ui/learning/diagnostic-run-session'
import { createReactDraftStoreMock } from './react-draft-store-mock'

const mocks = vi.hoisted(() => ({
  getCurrentAccess: vi.fn(),
  get: vi.fn(),
  post: vi.fn(),
}))
vi.mock('@tanstack/react-start', () => ({
  createServerFn: () => ({
    validator: (validate: (data: unknown) => unknown) => ({
      handler:
        (handler: (context: { data: unknown }) => Promise<unknown>) =>
        (context: { data: unknown }) =>
          handler({ data: validate(context.data) }),
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
const ids = {
  goalId: '01J00000000000000000000001',
  skillId: '01J00000000000000000000002',
  competencyId: '01J00000000000000000000003',
  activityId: '01J00000000000000000000004',
}
const wireActivity = {
  activity_id: ids.activityId,
  activity_revision: 'revision-react',
  title: 'Tela React',
  difficulty: 'easy',
  can_submit: true,
  questions: [
    {
      key: 'react-1',
      kind: 'react',
      prompt: 'Crie uma tela.',
      initial_files: [{ path: 'src/App.tsx', content: 'initial', editable: true }],
      editable_paths: ['src/App.tsx'],
      entrypoint: 'src/App.tsx',
      fixed_dependencies: [{ name: 'react', version: '19.0.0' }],
      permitted_commands: [{ id: 'dev', executable: 'npm', arguments: ['run', 'dev'] }],
      additional_file_policy: {
        allowed_directories: ['src'],
        allowed_extensions: ['.tsx'],
        max_files: 2,
      },
      criteria: [{ key: 'correct', name: 'Completude', weight_percentage: 100 }],
    },
  ],
}
const runId = 'f81d4fae-7dec-11d0-a765-00a0c91e6bf6'
const diagnostic: DiagnosticOverview = {
  status: 'diagnosing',
  runState: 'active',
  readyToComplete: false,
  nextCompetencyId: ids.competencyId,
  nextActivityId: ids.activityId,
  pendingAttemptId: null,
  pendingAttemptStatus: null,
  focusCompetencyId: null,
  competencies: [],
  initialOverallResult: null,
  overallCoverageComplete: true,
  directCompletion: false,
  activitySequence: [{ competencyId: ids.competencyId, activityId: ids.activityId }],
}
function setup(overrides: Partial<ActivityRouteProps> = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const store = createReactDraftStoreMock()
  const props: ActivityRouteProps = {
    ...ids,
    reactDraftStore: store,
    onNavigateToAttempt: vi.fn(),
    onUnsentAnswersChange: vi.fn(),
    onSessionExpired: vi.fn(),
    onNavigateToDiagnostic: vi.fn(),
    onNavigateToNextActivity: vi.fn(),
    onNavigateToResult: vi.fn(),
    ...overrides,
  }
  const view = renderHook(() => useActivityPage(props), {
    wrapper: ({ children }: { children: ReactNode }) =>
      createElement(QueryClientProvider, { client }, children),
  })
  return { ...view, store, client, props }
}
describe('useActivityPage route consumers', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    clearDiagnosticRun(ids.goalId, ids.skillId)
    vi.spyOn(window, 'scrollTo').mockImplementation(() => undefined)
    mocks.getCurrentAccess.mockResolvedValue({
      accountId: 'account-1',
      accessToken: 'token',
    })
    mocks.get.mockResolvedValue(new RestResponse({ statusCode: 200, body: wireActivity }))
    mocks.post.mockResolvedValue(
      new RestResponse({
        statusCode: 200,
        body: { status: 'inconclusive', score: null },
      }),
    )
  })
  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
    clearDiagnosticRun(ids.goalId, ids.skillId)
  })

  it('maps the React wire contract through the real service into the activity consumer', async () => {
    const { result } = setup()
    await waitFor(() => expect(result.current.activity?.title).toBe('Tela React'))
    expect(mocks.get).toHaveBeenCalledWith(learningActivityPath(ids), {
      headers: { Authorization: 'Bearer token' },
    })
    expect(result.current.currentQuestion).toMatchObject({
      kind: 'react',
      initialFiles: wireActivity.questions[0].initial_files,
      fixedDependencies: [{ name: 'react', version: '19.0.0' }],
      additionalFilePolicy: {
        allowedDirectories: ['src'],
        allowedExtensions: ['.tsx'],
        maxFiles: 2,
      },
      criteria: [{ key: 'correct', name: 'Completude', weightPercentage: 100 }],
    })
    expect(result.current.accountId).toBe('account-1')
    expect(result.current.isOnlineAuthority).toBe(true)
  })

  it('retains identity and the frozen React result during a background refetch', async () => {
    const { result } = setup()
    await waitFor(() => expect(result.current.isOnlineAuthority).toBe(true))
    const files = [{ path: 'src/App.tsx', content: 'frozen source' }]
    await act(async () => result.current.handleAssessCode(files))
    expect(result.current.feedback?.status).toBe('inconclusive')
    let complete: (response: RestResponse<typeof wireActivity>) => void = () => undefined
    mocks.get.mockReturnValueOnce(
      new Promise<RestResponse<typeof wireActivity>>((resolve) => {
        complete = resolve
      }),
    )
    let pending: ReturnType<typeof result.current.handleRetryLoad>
    act(() => {
      pending = result.current.handleRetryLoad()
    })
    await waitFor(() => expect(mocks.get).toHaveBeenCalledTimes(2))
    expect(result.current.accountId).toBe('account-1')
    expect(result.current.isOnlineAuthority).toBe(true)
    act(() =>
      result.current.handleCodeFilesChange([
        { path: 'src/App.tsx', content: 'other tab' },
      ]),
    )
    expect(result.current.frozenAnswer).toEqual({
      kind: 'react',
      questionKey: 'react-1',
      files,
    })
    expect(result.current.feedback?.status).toBe('inconclusive')
    await act(async () => {
      complete(new RestResponse({ statusCode: 200, body: structuredClone(wireActivity) }))
      await pending
    })
    await act(async () => result.current.handleContinue())
    expect(mocks.post.mock.calls[1]).toEqual(mocks.post.mock.calls[0])
    expect(result.current.frozenAnswer).toMatchObject({ kind: 'react', files })
  })

  it('tombstones an authenticated uncached 404 using route identity', async () => {
    mocks.get.mockResolvedValue(new RestResponse({ statusCode: 404 }))
    const { result, store } = setup()
    await waitFor(() => expect(result.current.isPrivateAbsence).toBe(true))
    await waitFor(() =>
      expect(store.tombstoneActivity).toHaveBeenCalledWith('account-1', ids.activityId),
    )
    expect(result.current.activity).toBeNull()
  })

  it('keeps an authenticated missing activity inaccessible when local cleanup fails', async () => {
    const store = createReactDraftStoreMock()
    vi.mocked(store.tombstoneActivity).mockRejectedValue(
      new Error('IndexedDB unavailable'),
    )
    mocks.get.mockResolvedValue(new RestResponse({ statusCode: 404 }))
    const { result } = setup({ reactDraftStore: store })
    await waitFor(() =>
      expect(store.tombstoneActivity).toHaveBeenCalledWith('account-1', ids.activityId),
    )
    expect(result.current.isPrivateAbsence).toBe(true)
    expect(result.current.activity).toBeNull()
    expect(result.current.isOnlineAuthority).toBe(false)
  })

  it('keeps local drafts when the session has expired', async () => {
    mocks.getCurrentAccess.mockResolvedValue(null)
    const { result, store } = setup()
    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.isOnlineAuthority).toBe(false)
    expect(store.tombstoneActivity).not.toHaveBeenCalled()
  })

  it('fails closed when the activity contains an unknown wire question kind', async () => {
    mocks.get.mockResolvedValue(
      new RestResponse({
        statusCode: 200,
        body: {
          ...wireActivity,
          questions: [{ key: 'unknown', kind: 'unknown', prompt: 'Invalid' }],
        },
      }),
    )
    const { result } = setup()
    await waitFor(() => expect(result.current.isRecoverableError).toBe(true))
    expect(result.current.activity).toBeNull()
    expect(result.current.isOnlineAuthority).toBe(false)
  })

  it.each([401, 429, 503])(
    'maps HTTP %s and preserves drafts while allowing retry',
    async (statusCode) => {
      mocks.get.mockResolvedValueOnce(new RestResponse({ statusCode }))
      const { result, props, store } = setup()
      await waitFor(() => expect(result.current.isLoading).toBe(false))
      expect(result.current.isRecoverableError).toBe(statusCode !== 401)
      expect(result.current.isPrivateAbsence).toBe(false)
      if (statusCode === 401) expect(props.onSessionExpired).toHaveBeenCalled()
      expect(store.tombstoneActivity).not.toHaveBeenCalled()
      await act(async () => {
        await result.current.handleRetryLoad()
      })
      await waitFor(() => expect(result.current.activity?.title).toBe('Tela React'))
      expect(result.current.isOnlineAuthority).toBe(true)
    },
  )

  it('recovers from an unavailable authentication provider without deleting drafts', async () => {
    mocks.getCurrentAccess.mockRejectedValueOnce(
      new AuthError('unavailable', 'Offline', { statusCode: 503 }),
    )
    const { result } = setup()
    await waitFor(() => expect(result.current.isRecoverableError).toBe(true))
    await act(async () => {
      await result.current.handleRetryLoad()
    })
    await waitFor(() => expect(result.current.activity?.activityId).toBe(ids.activityId))
  })

  it.each([false, true])(
    'redirects an unresolved attempt according to diagnostic ownership=%s',
    async (isDiagnostic) => {
      mocks.get.mockResolvedValue(
        new RestResponse({
          statusCode: 200,
          body: {
            ...wireActivity,
            is_diagnostic: isDiagnostic,
            unresolved_attempt_id: 'unresolved',
          },
        }),
      )
      const { props } = setup()
      await waitFor(() =>
        expect(
          isDiagnostic ? props.onNavigateToDiagnostic : props.onNavigateToAttempt,
        ).toHaveBeenCalled(),
      )
      if (!isDiagnostic)
        expect(props.onNavigateToAttempt).toHaveBeenCalledWith('unresolved', true)
    },
  )

  it('requires a fresh diagnostic entry for a conflicting activity without run identity', async () => {
    mocks.get.mockResolvedValue(new RestResponse({ statusCode: 409 }))
    const { result, props } = setup()
    await waitFor(() => expect(result.current.isDiagnosticEntryRequired).toBe(true))
    expect(props.onNavigateToDiagnostic).toHaveBeenCalledOnce()
    expect(result.current.isInvalidated).toBe(false)
  })

  it('does not request the server for malformed route identifiers', async () => {
    const { result } = setup({ activityId: 'bad' })
    await waitFor(() => expect(result.current.isRecoverableError).toBe(true))
    expect(mocks.get).not.toHaveBeenCalled()
    expect(mocks.getCurrentAccess).not.toHaveBeenCalled()
  })

  it('revokes online authority offline and restores it after a successful authenticated refresh', async () => {
    const { result } = setup()
    await waitFor(() => expect(result.current.isOnlineAuthority).toBe(true))
    const navigatorOnlineMock = vi
      .spyOn(navigator, 'onLine', 'get')
      .mockReturnValue(false)
    act(() => window.dispatchEvent(new Event('offline')))
    expect(result.current.isOnlineAuthority).toBe(false)
    navigatorOnlineMock.mockReturnValue(true)
    act(() => window.dispatchEvent(new Event('online')))
    await waitFor(() => expect(result.current.isOnlineAuthority).toBe(true))
    expect(mocks.get.mock.calls.length).toBeGreaterThan(1)
  })

  it('maps preliminary rubric files and submits the frozen React answer through the real service', async () => {
    mocks.post.mockResolvedValueOnce(
      new RestResponse({
        statusCode: 200,
        body: {
          status: 'conclusive',
          score: 75,
          is_correct: true,
          explanation: 'Resultado',
          submitted_files: [{ path: 'src/App.tsx', content: 'snapshot' }],
          criteria: [
            {
              key: 'correct',
              weight_percentage: 100,
              level: '75',
              comment_id: 'ok',
              comment: 'Quase completo',
            },
          ],
        },
      }),
    )
    mocks.post.mockResolvedValueOnce(
      new RestResponse({
        statusCode: 200,
        body: { attempt_id: 'attempt-real', status: 'pending', result_url: '/result' },
      }),
    )
    const { result, props, store } = setup()
    await waitFor(() => expect(result.current.isOnlineAuthority).toBe(true))
    const files = [{ path: 'src/App.tsx', content: 'snapshot' }]
    act(() => result.current.handleCodeFilesChange(files))
    await act(async () => result.current.handleAssessCode(files))
    expect(result.current.feedback).toMatchObject({
      score: 75,
      isCorrect: true,
      submittedFiles: files,
      criteria: [
        {
          key: 'correct',
          weightPercentage: 100,
          level: '75',
          commentId: 'ok',
          comment: 'Quase completo',
        },
      ],
    })
    await act(async () => result.current.handleContinue())
    await waitFor(() =>
      expect(props.onNavigateToAttempt).toHaveBeenCalledWith('attempt-real'),
    )
    expect(mocks.post.mock.calls[1][1]).toMatchObject({
      activity_revision: 'revision-react',
      answers: [{ kind: 'react', question_key: 'react-1', files }],
    })
    expect(store.tombstoneActivity).toHaveBeenCalledWith('account-1', ids.activityId)
    expect(result.current.hasUnsentAnswers).toBe(false)
    await act(async () => result.current.handleContinue())
    expect(mocks.post).toHaveBeenCalledTimes(2)
  })

  it('keeps an accepted submission successful when local draft cleanup rejects', async () => {
    const store = createReactDraftStoreMock()
    vi.mocked(store.tombstoneActivity).mockRejectedValue(
      new Error('IndexedDB unavailable'),
    )
    mocks.post.mockResolvedValueOnce(
      new RestResponse({ statusCode: 200, body: { status: 'conclusive', score: 100 } }),
    )
    mocks.post.mockResolvedValueOnce(
      new RestResponse({
        statusCode: 200,
        body: { attempt_id: 'accepted', status: 'pending', result_url: '/result' },
      }),
    )
    const { result, props } = setup({ reactDraftStore: store })
    await waitFor(() => expect(result.current.isOnlineAuthority).toBe(true))
    const files = [{ path: 'src/App.tsx', content: 'accepted source' }]
    act(() => result.current.handleCodeFilesChange(files))
    await act(async () => result.current.handleAssessCode(files))
    await act(async () => result.current.handleContinue())
    await waitFor(() =>
      expect(props.onNavigateToAttempt).toHaveBeenCalledWith('accepted'),
    )
    expect(result.current.hasSubmissionError).toBe(false)
    expect(result.current.hasUnsentAnswers).toBe(false)
  })

  it.each([401, 404, 409, 422, 429])(
    'preserves the exact frozen source after preliminary HTTP %s',
    async (statusCode) => {
      const { result } = setup()
      await waitFor(() => expect(result.current.isOnlineAuthority).toBe(true))
      mocks.post.mockResolvedValueOnce(new RestResponse({ statusCode }))
      const files = [{ path: 'src/App.tsx', content: 'frozen' }]
      await act(async () => result.current.handleAssessCode(files))
      expect(result.current.hasFeedbackError).toBe(true)
      expect(result.current.frozenAnswer).toMatchObject({ kind: 'react', files })
      await act(async () => result.current.handleContinue())
      expect(result.current.feedback?.status).toBe('inconclusive')
      expect(mocks.post.mock.calls[1]).toEqual(mocks.post.mock.calls[0])
    },
  )

  it('rejects preliminary evaluation after authentication expires without losing the answer', async () => {
    const { result } = setup()
    await waitFor(() => expect(result.current.isOnlineAuthority).toBe(true))
    mocks.getCurrentAccess.mockResolvedValue(null)
    await act(async () =>
      result.current.handleAssessCode([{ path: 'src/App.tsx', content: 'local' }]),
    )
    expect(result.current.hasFeedbackError).toBe(true)
    expect(mocks.post).not.toHaveBeenCalled()
  })

  it('stages a diagnostic activity and navigates before submitting the consolidated run', async () => {
    setDiagnosticRun(ids.goalId, ids.skillId, runId)
    const next = {
      competencyId: '01J00000000000000000000005',
      activityId: '01J00000000000000000000006',
    }
    mocks.get.mockImplementation(
      async (path: string) =>
        new RestResponse({
          statusCode: 200,
          body: path.endsWith('/diagnostic')
            ? {
                ...diagnostic,
                activitySequence: [...(diagnostic.activitySequence ?? []), next],
              }
            : { ...wireActivity, is_diagnostic: true },
        }),
    )
    const { result, props } = setup({ diagnosticRunId: runId })
    await waitFor(() => expect(result.current.activity?.isDiagnostic).toBe(true))
    await waitFor(() =>
      expect(getDiagnosticRun(ids.goalId, ids.skillId)?.sequence).toHaveLength(2),
    )
    act(() =>
      result.current.handleCodeFilesChange([
        { path: 'src/App.tsx', content: 'diagnostic' },
      ]),
    )
    await act(async () => result.current.handleContinue())
    expect(props.onNavigateToNextActivity).toHaveBeenCalledWith(
      next.competencyId,
      next.activityId,
    )
    expect(getDiagnosticRun(ids.goalId, ids.skillId)?.answers.size).toBe(1)
    expect(mocks.post).not.toHaveBeenCalled()
  })

  it('submits all diagnostic answers with run identity and waits for evaluation', async () => {
    setDiagnosticRun(ids.goalId, ids.skillId, runId)
    mocks.get.mockImplementation(
      async (path: string) =>
        new RestResponse({
          statusCode: 200,
          body: path.endsWith('/diagnostic')
            ? diagnostic
            : { ...wireActivity, is_diagnostic: true },
        }),
    )
    mocks.post.mockResolvedValue(
      new RestResponse({ statusCode: 200, body: { status: 'pending', replayed: false } }),
    )
    const { result } = setup({ diagnosticRunId: runId })
    await waitFor(() => expect(result.current.activity?.isDiagnostic).toBe(true))
    await waitFor(() =>
      expect(getDiagnosticRun(ids.goalId, ids.skillId)?.sequence).toHaveLength(1),
    )
    act(() =>
      result.current.handleCodeFilesChange([
        { path: 'src/App.tsx', content: 'diagnostic' },
      ]),
    )
    await act(async () => result.current.handleContinue())
    await waitFor(() => expect(result.current.isDiagnosticProcessing).toBe(true))
    expect(mocks.post).toHaveBeenCalledWith(
      expect.stringContaining('/diagnostic/submissions'),
      {
        submission_key: expect.any(String),
        items: [
          {
            competency_id: ids.competencyId,
            activity_id: ids.activityId,
            activity_revision: 'revision-react',
            answers: [
              {
                kind: 'react',
                question_key: 'react-1',
                files: [{ path: 'src/App.tsx', content: 'diagnostic' }],
              },
            ],
          },
        ],
      },
      { headers: { Authorization: 'Bearer token', 'X-Diagnostic-Run-Id': runId } },
    )
    expect(result.current.isSubmissionLocked).toBe(true)
    expect(result.current.hasUnsentAnswers).toBe(false)
  })

  it('retains diagnostic answers and a stable key after submission fails', async () => {
    setDiagnosticRun(ids.goalId, ids.skillId, runId)
    mocks.get.mockImplementation(
      async (path: string) =>
        new RestResponse({
          statusCode: 200,
          body: path.endsWith('/diagnostic')
            ? diagnostic
            : { ...wireActivity, is_diagnostic: true },
        }),
    )
    mocks.post
      .mockResolvedValueOnce(new RestResponse({ statusCode: 503 }))
      .mockResolvedValueOnce(
        new RestResponse({
          statusCode: 200,
          body: { status: 'pending', replayed: false },
        }),
      )
    const { result } = setup({ diagnosticRunId: runId })
    await waitFor(() =>
      expect(getDiagnosticRun(ids.goalId, ids.skillId)?.sequence).toHaveLength(1),
    )
    act(() =>
      result.current.handleCodeFilesChange([
        { path: 'src/App.tsx', content: 'retryable' },
      ]),
    )
    await act(async () => result.current.handleContinue())
    expect(result.current.hasSubmissionError).toBe(true)
    expect(result.current.hasUnsentAnswers).toBe(true)
    await act(async () => result.current.handleContinue())
    expect(mocks.post.mock.calls[1]).toEqual(mocks.post.mock.calls[0])
  })

  it('blocks consolidated submission when an earlier diagnostic activity has no staged answer', async () => {
    setDiagnosticRun(ids.goalId, ids.skillId, runId)
    const previous = {
      competencyId: '01J00000000000000000000005',
      activityId: '01J00000000000000000000006',
    }
    mocks.get.mockImplementation(
      async (path: string) =>
        new RestResponse({
          statusCode: 200,
          body: path.endsWith('/diagnostic')
            ? {
                ...diagnostic,
                activitySequence: [previous, ...(diagnostic.activitySequence ?? [])],
              }
            : { ...wireActivity, is_diagnostic: true },
        }),
    )
    const { result } = setup({ diagnosticRunId: runId })
    await waitFor(() =>
      expect(getDiagnosticRun(ids.goalId, ids.skillId)?.sequence).toHaveLength(2),
    )
    act(() =>
      result.current.handleCodeFilesChange([{ path: 'src/App.tsx', content: 'latest' }]),
    )
    await act(async () => result.current.handleContinue())
    expect(result.current.hasSubmissionError).toBe(true)
    expect(mocks.post).not.toHaveBeenCalled()
  })

  it.each([false, true])(
    'restores diagnostic processing from a conflict: readyToComplete=%s',
    async (readyToComplete) => {
      setDiagnosticRun(ids.goalId, ids.skillId, runId)
      mocks.get.mockImplementation(async (path: string) =>
        path.endsWith('/diagnostic')
          ? new RestResponse({
              statusCode: 200,
              body: {
                ...diagnostic,
                readyToComplete,
                pendingAttemptId: '01J00000000000000000000007',
                pendingAttemptStatus: 'pending',
              },
            })
          : new RestResponse({ statusCode: 409 }),
      )
      const { result } = setup({ diagnosticRunId: runId })
      await waitFor(() => expect(result.current.isDiagnosticProcessing).toBe(true))
      expect(result.current.activity).toBeNull()
      expect(result.current.isRecoverableError).toBe(false)
      expect(result.current.diagnosticStatus).toBe('pending')
    },
  )

  it('clears a stale run and delegates return to the skill entry', async () => {
    setDiagnosticRun(ids.goalId, ids.skillId, runId)
    mocks.get.mockResolvedValue(new RestResponse({ statusCode: 409 }))
    const { result, props } = setup({ diagnosticRunId: runId })
    await waitFor(() => expect(result.current.isInvalidated).toBe(true))
    expect(getDiagnosticRun(ids.goalId, ids.skillId)).toBeNull()
    act(() => result.current.handleReturnToSkill())
    expect(props.onNavigateToDiagnostic).toHaveBeenCalledOnce()
  })

  it.each(['learning', 'completed'] as const)(
    'navigates to the consolidated result after diagnostic status becomes %s',
    async (status) => {
      setDiagnosticRun(ids.goalId, ids.skillId, runId)
      mocks.get.mockImplementation(
        async (path: string) =>
          new RestResponse({
            statusCode: 200,
            body: path.endsWith('/diagnostic') ? { ...diagnostic, status } : wireActivity,
          }),
      )
      const { props } = setup({ diagnosticRunId: runId })
      await waitFor(() => expect(props.onNavigateToResult).toHaveBeenCalled())
      expect(getDiagnosticRun(ids.goalId, ids.skillId)).toBeNull()
    },
  )

  it('retries a failed diagnostic evaluation and refreshes its status', async () => {
    setDiagnosticRun(ids.goalId, ids.skillId, runId)
    let pendingAttemptStatus = 'failed'
    mocks.get.mockImplementation(
      async (path: string) =>
        new RestResponse({
          statusCode: 200,
          body: path.endsWith('/diagnostic')
            ? {
                ...diagnostic,
                pendingAttemptStatus,
                pendingAttemptId: '01J00000000000000000000007',
              }
            : wireActivity,
        }),
    )
    mocks.post
      .mockResolvedValueOnce(new RestResponse({ statusCode: 503 }))
      .mockImplementationOnce(async () => {
        pendingAttemptStatus = 'pending'
        return new RestResponse({ statusCode: 200 })
      })
    const { result } = setup({ diagnosticRunId: runId })
    await waitFor(() => expect(result.current.diagnosticStatus).toBe('failed'))
    await act(async () => result.current.handleRetryDiagnostic())
    expect(result.current.diagnosticRetryError).toBe(true)
    await act(async () => result.current.handleRetryDiagnostic())
    expect(result.current.diagnosticRetryError).toBe(false)
    await waitFor(() => expect(result.current.diagnosticStatus).toBe('pending'))
    expect(mocks.post.mock.calls[1][2]).toEqual({
      headers: { Authorization: 'Bearer token', 'X-Diagnostic-Run-Id': runId },
    })
    await act(async () => result.current.handleRetryDiagnostic())
    expect(mocks.post).toHaveBeenCalledTimes(2)
  })

  it('retries status retrieval without discarding a private draft', async () => {
    mocks.get.mockImplementation(async (path: string) =>
      path.endsWith('/diagnostic')
        ? new RestResponse({ statusCode: 503 })
        : new RestResponse({ statusCode: 200, body: wireActivity }),
    )
    const { result } = setup({ diagnosticRunId: runId })
    await waitFor(() => expect(result.current.hasDiagnosticStatusError).toBe(true))
    mocks.get.mockImplementation(
      async (path: string) =>
        new RestResponse({
          statusCode: 200,
          body: path.endsWith('/diagnostic') ? diagnostic : wireActivity,
        }),
    )
    await act(async () => result.current.handleRetryDiagnosticStatus())
    await waitFor(() => expect(result.current.hasDiagnosticStatusError).toBe(false))
  })

  it('retries failed automatic consolidation once the user requests recovery', async () => {
    setDiagnosticRun(ids.goalId, ids.skillId, runId)
    mocks.get.mockImplementation(
      async (path: string) =>
        new RestResponse({
          statusCode: 200,
          body: path.endsWith('/diagnostic')
            ? { ...diagnostic, runState: 'ready_to_complete', readyToComplete: true }
            : wireActivity,
        }),
    )
    mocks.post
      .mockResolvedValueOnce(new RestResponse({ statusCode: 503 }))
      .mockResolvedValueOnce(
        new RestResponse({ statusCode: 200, body: { status: 'learning' } }),
      )
    const { result, props } = setup({ diagnosticRunId: runId })
    await waitFor(() => expect(result.current.diagnosticCompletionError).toBe(true))
    expect(props.onNavigateToResult).not.toHaveBeenCalled()
    await act(async () => result.current.handleRetryDiagnosticCompletion())
    await waitFor(() => expect(props.onNavigateToResult).toHaveBeenCalled())
    expect(mocks.post).toHaveBeenCalledTimes(2)
    expect(getDiagnosticRun(ids.goalId, ids.skillId)).toBeNull()
  })
})
