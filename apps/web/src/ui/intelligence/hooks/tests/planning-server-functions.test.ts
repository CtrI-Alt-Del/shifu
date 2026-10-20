import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import type { RestClient } from '@/core/shared/interfaces/rest-client'
import { RestResponse } from '@/core/shared/responses/rest-response'
import { planningFailure } from '@/provision/planning/planning-server-provider'

import { PlanningRequestError, unwrapPlanningResult } from '../planning-request-error'
import { answerPlanningQuestionsServer } from '../use-answer-planning-questions-action'
import { cancelPlanningServer } from '../use-cancel-planning-action'
import { getPlanningSessionServer } from '../use-planning-session-query'
import { confirmPlanningServer } from '../use-confirm-planning-action'
import { restartPlanningServer } from '../use-restart-planning-action'
import { retryPlanningServer } from '../use-retry-planning-action'

const mocks = vi.hoisted(() => ({
  request: new Request('http://shifu.test/intelligence/planner'),
  getCurrentAccess: vi.fn(),
  axiosRestClient: vi.fn(),
  intelligenceService: vi.fn(),
  service: {
    getPlanningSession: vi.fn(),
    answerPlanningQuestions: vi.fn(),
    retryPlanning: vi.fn(),
    restartPlanning: vi.fn(),
    confirmPlanning: vi.fn(),
    cancelPlanning: vi.fn(),
  },
}))

vi.mock('@tanstack/react-start', () => ({
  createServerFn: () => ({
    validator: (validate: (data: unknown) => unknown) => ({
      handler:
        (handler: (context: { data: unknown }) => Promise<unknown>) =>
        async (context: { data: unknown }) =>
          handler({ data: validate(context.data) }),
    }),
  }),
}))

vi.mock('@tanstack/react-start/server', () => ({
  getRequest: () => mocks.request,
}))

vi.mock('@/constants/server-env', () => ({
  SERVER_ENV: { shifuServerAppUrl: 'http://shifu.test' },
}))

vi.mock('@/provision/auth/better-auth/better-auth-provider', () => ({
  getBetterAuthProvider: () => ({ getCurrentAccess: mocks.getCurrentAccess }),
}))

vi.mock('@/rest/axios/axios-rest-client', () => ({
  AxiosRestClient: mocks.axiosRestClient,
}))

vi.mock('@/rest/services/intelligence-service', () => ({
  IntelligenceService: mocks.intelligenceService,
}))

const CONFIRMATION_KEY = '3f0c2b9e-8d1a-4c57-9b2e-6a1d4f8c0e21'
const PLANNING_ID = '01ARZ3NDEKTSV4RRFFQ69G5FAV'

describe('Planner server functions', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mocks.getCurrentAccess.mockResolvedValue({
      accessToken: 'access-token',
      email: 'learner@shifu.local',
    })
    mocks.axiosRestClient.mockReturnValue({ restClient: true })
    mocks.intelligenceService.mockReturnValue(mocks.service)
    mocks.service.getPlanningSession.mockResolvedValue({ id: PLANNING_ID })
    mocks.service.answerPlanningQuestions.mockResolvedValue({ status: 'processing' })
    mocks.service.retryPlanning.mockResolvedValue({ status: 'processing' })
    mocks.service.restartPlanning.mockResolvedValue({
      status: 'processing',
      generation: 2,
    })
    mocks.service.confirmPlanning.mockResolvedValue({ goalId: 'goal-1', replayed: false })
    mocks.service.cancelPlanning.mockResolvedValue(undefined)
  })

  it('derives access from the request and forwards each planning operation', async () => {
    await getPlanningSessionServer({ data: { planningId: PLANNING_ID } })
    await answerPlanningQuestionsServer({
      data: {
        planningId: PLANNING_ID,
        batchId: 'batch-1',
        answers: [{ questionId: 'q1', optionIds: ['a', 'nao-sei'] }],
      },
    })
    await retryPlanningServer({ data: { planningId: PLANNING_ID } })
    await restartPlanningServer({
      data: { planningId: PLANNING_ID, initialIntent: '  Quero aprender APIs  ' },
    })
    await confirmPlanningServer({
      data: {
        planningId: PLANNING_ID,
        confirmationKey: CONFIRMATION_KEY,
        title: '  Automação  ',
        description: ' Scripts ',
      },
    })
    const cancelled = await cancelPlanningServer({ data: { planningId: PLANNING_ID } })

    expect(mocks.getCurrentAccess).toHaveBeenCalledTimes(6)
    expect(mocks.getCurrentAccess).toHaveBeenCalledWith(mocks.request)
    expect(mocks.axiosRestClient).toHaveBeenCalledWith('http://shifu.test', {
      withCredentials: false,
    })
    expect(mocks.service.getPlanningSession).toHaveBeenCalledWith(
      'access-token',
      PLANNING_ID,
    )
    expect(mocks.service.answerPlanningQuestions).toHaveBeenCalledWith(
      'access-token',
      PLANNING_ID,
      {
        batchId: 'batch-1',
        answers: [{ questionId: 'q1', optionIds: ['a', 'nao-sei'] }],
      },
    )
    expect(mocks.service.retryPlanning).toHaveBeenCalledWith('access-token', PLANNING_ID)
    expect(mocks.service.restartPlanning).toHaveBeenCalledWith(
      'access-token',
      PLANNING_ID,
      'Quero aprender APIs',
    )
    expect(mocks.service.confirmPlanning).toHaveBeenCalledWith(
      'access-token',
      PLANNING_ID,
      { confirmationKey: CONFIRMATION_KEY, title: 'Automação', description: 'Scripts' },
    )
    expect(mocks.service.cancelPlanning).toHaveBeenCalledWith('access-token', PLANNING_ID)
    expect(cancelled).toEqual({ cancelled: true })
  })

  it('rejects malformed input before reaching the service', async () => {
    await expect(
      getPlanningSessionServer({ data: { planningId: 'not-a-ulid' } }),
    ).rejects.toThrow()
    await expect(
      answerPlanningQuestionsServer({
        data: { planningId: PLANNING_ID, batchId: 'batch-1', answers: [] },
      }),
    ).rejects.toThrow()
    await expect(
      answerPlanningQuestionsServer({
        data: {
          planningId: PLANNING_ID,
          batchId: 'batch-1',
          answers: [{ questionId: 'q1', optionIds: ['a'], text: 'livre' }],
        },
      }),
    ).rejects.toThrow()
    await expect(
      retryPlanningServer({ data: { planningId: PLANNING_ID, extra: true } }),
    ).rejects.toThrow()
    await expect(
      restartPlanningServer({ data: { planningId: PLANNING_ID, initialIntent: '   ' } }),
    ).rejects.toThrow()
    await expect(
      restartPlanningServer({
        data: { planningId: PLANNING_ID, initialIntent: 'x'.repeat(4001) },
      }),
    ).rejects.toThrow()
    expect(mocks.service.restartPlanning).not.toHaveBeenCalled()
    await expect(
      confirmPlanningServer({
        data: {
          planningId: PLANNING_ID,
          confirmationKey: 'nope',
          title: 'T',
          description: 'D',
        },
      }),
    ).rejects.toThrow()
    await expect(
      confirmPlanningServer({
        data: {
          planningId: PLANNING_ID,
          confirmationKey: CONFIRMATION_KEY,
          title: ' ',
          description: 'D',
        },
      }),
    ).rejects.toThrow()
    expect(mocks.service.confirmPlanning).not.toHaveBeenCalled()
    expect(mocks.service.getPlanningSession).not.toHaveBeenCalled()
    expect(mocks.service.answerPlanningQuestions).not.toHaveBeenCalled()
    expect(mocks.service.retryPlanning).not.toHaveBeenCalled()
  })

  it('returns typed failures instead of throwing across the server boundary', async () => {
    mocks.getCurrentAccess.mockResolvedValueOnce(null)
    expect(await getPlanningSessionServer({ data: { planningId: PLANNING_ID } })).toEqual(
      {
        kind: 'unauthorized',
      },
    )

    mocks.service.getPlanningSession.mockRejectedValueOnce(new RestError('missing', 404))
    expect(await getPlanningSessionServer({ data: { planningId: PLANNING_ID } })).toEqual(
      {
        kind: 'not-found',
      },
    )

    mocks.service.retryPlanning.mockRejectedValueOnce(
      new RestError('Já existe uma operação em andamento neste planejamento.', 409),
    )
    expect(await retryPlanningServer({ data: { planningId: PLANNING_ID } })).toEqual({
      kind: 'conflict',
      message: 'Já existe uma operação em andamento neste planejamento.',
    })

    mocks.service.answerPlanningQuestions.mockRejectedValueOnce(
      new RestError('Responda todas as perguntas.', 400),
    )
    expect(
      await answerPlanningQuestionsServer({
        data: {
          planningId: PLANNING_ID,
          batchId: 'batch-1',
          answers: [{ questionId: 'q1', optionIds: [] }],
        },
      }),
    ).toEqual({ kind: 'invalid-request', message: 'Responda todas as perguntas.' })

    mocks.service.cancelPlanning.mockRejectedValueOnce(new RestError('boom', 503))
    expect(await cancelPlanningServer({ data: { planningId: PLANNING_ID } })).toEqual({
      kind: 'unavailable',
    })
  })

  it('maps every failure class to a planning failure kind', () => {
    expect(planningFailure(new AuthError('unavailable', 'down'))).toEqual({
      kind: 'unavailable',
    })
    expect(planningFailure(new AuthError('authentication-rejected', 'nope'))).toEqual({
      kind: 'unauthorized',
    })
    expect(planningFailure(new RestError('expired', 401))).toEqual({
      kind: 'unauthorized',
    })
    expect(planningFailure(new RestError('invalid', 422))).toEqual({
      kind: 'invalid-request',
      message: 'invalid',
    })
    expect(planningFailure(new RestError('oops', 500))).toEqual({ kind: 'unavailable' })
    expect(planningFailure(new Error('socket'))).toEqual({ kind: 'unavailable' })
  })

  it('unwraps results and raises typed errors on the client', () => {
    expect(unwrapPlanningResult({ id: PLANNING_ID })).toEqual({ id: PLANNING_ID })
    expect(() => unwrapPlanningResult({ kind: 'conflict', message: 'ocupado' })).toThrow(
      PlanningRequestError,
    )
    try {
      unwrapPlanningResult({ kind: 'not-found' })
    } catch (error) {
      expect(error).toBeInstanceOf(PlanningRequestError)
      expect((error as PlanningRequestError).kind).toBe('not-found')
      expect((error as PlanningRequestError).message).toBe('Planejamento não encontrado.')
    }
    expect(() => unwrapPlanningResult({ kind: 'unknown' })).not.toThrow()
  })

  it('maps the REST contract of the planner through the real service', async () => {
    const { IntelligenceService: createIntelligenceService } = await vi.importActual<
      typeof import('@/rest/services/intelligence-service')
    >('@/rest/services/intelligence-service')
    const calls: { method: string; url: string; body?: unknown }[] = []
    const detail = {
      id: PLANNING_ID,
      status: 'interview',
      intent: 'Quero aprender web',
      generation: 2,
      created_at: '2026-10-20T12:00:00Z',
      updated_at: '2026-10-20T12:01:00Z',
      operation: null,
      consulted_curriculum: true,
      batch: {
        id: 'batch-1',
        questions: [
          {
            id: 'q1',
            text: 'O que você quer construir?',
            kind: 'single',
            options: [
              { id: 'o1', text: 'Sites', exclusive: false },
              { id: 'nao-sei', text: 'Não sei', exclusive: true },
            ],
          },
        ],
      },
      answered_batch_count: 1,
      proposal: null,
      message: null,
      failure_code: null,
    }
    const processing = {
      ...detail,
      status: 'processing',
      batch: null,
      operation: {
        kind: 'answer',
        started_at: '2026-10-20T12:02:00Z',
        stage: 'composing',
      },
    }
    const proposed = {
      ...detail,
      status: 'proposal',
      batch: null,
      operation: { kind: 'start', started_at: '2026-10-20T12:02:00Z' },
      proposal: {
        title: 'Aprender web',
        description: 'Do HTML ao React.',
        skills: [{ skill_id: 'skill-html', name: 'HTML e CSS', justification: 'Base.' }],
        relations: [{ skill_id: 'skill-react', foundation_skill_id: 'skill-html' }],
      },
    }
    const restClient = {
      get: vi.fn(async (url: string) => {
        calls.push({ method: 'GET', url })
        return new RestResponse({ body: detail, statusCode: 200 })
      }),
      post: vi.fn(async (url: string, body: unknown) => {
        calls.push({ method: 'POST', url, body })
        return new RestResponse({
          body: url.endsWith('/confirm')
            ? { goal_id: 'goal-1', replayed: true }
            : url.endsWith('/retry')
              ? proposed
              : processing,
          statusCode: url.endsWith('/confirm') ? 200 : 202,
        })
      }),
      delete: vi.fn(async (url: string) => {
        calls.push({ method: 'DELETE', url })
        return new RestResponse({ statusCode: 204 })
      }),
    } as unknown as RestClient
    mocks.intelligenceService.mockImplementation(() =>
      createIntelligenceService(restClient),
    )

    const session = await getPlanningSessionServer({ data: { planningId: PLANNING_ID } })
    const answered = await answerPlanningQuestionsServer({
      data: {
        planningId: PLANNING_ID,
        batchId: 'batch-1',
        answers: [{ questionId: 'q1', optionIds: ['o1'] }],
      },
    })
    const retried = await retryPlanningServer({ data: { planningId: PLANNING_ID } })
    const restarted = await restartPlanningServer({
      data: { planningId: PLANNING_ID, initialIntent: 'Quero aprender APIs' },
    })
    const confirmed = await confirmPlanningServer({
      data: {
        planningId: PLANNING_ID,
        confirmationKey: CONFIRMATION_KEY,
        title: 'Automação',
        description: 'Scripts',
      },
    })
    await cancelPlanningServer({ data: { planningId: PLANNING_ID } })

    expect(calls).toEqual([
      { method: 'GET', url: `/intelligence/planning-sessions/${PLANNING_ID}` },
      {
        method: 'POST',
        url: `/intelligence/planning-sessions/${PLANNING_ID}/answers`,
        body: {
          batch_id: 'batch-1',
          answers: [{ question_id: 'q1', option_ids: ['o1'] }],
        },
      },
      {
        method: 'POST',
        url: `/intelligence/planning-sessions/${PLANNING_ID}/retry`,
        body: undefined,
      },
      {
        method: 'POST',
        url: `/intelligence/planning-sessions/${PLANNING_ID}/restart`,
        body: { initial_intent: 'Quero aprender APIs' },
      },
      {
        method: 'POST',
        url: `/intelligence/planning-sessions/${PLANNING_ID}/confirm`,
        body: {
          confirmation_key: CONFIRMATION_KEY,
          title: 'Automação',
          description: 'Scripts',
        },
      },
      { method: 'DELETE', url: `/intelligence/planning-sessions/${PLANNING_ID}` },
    ])
    expect(restClient.get).toHaveBeenCalledWith(expect.any(String), {
      headers: { Authorization: 'Bearer access-token', 'Cache-Control': 'no-store' },
    })
    expect(session).toEqual({
      id: PLANNING_ID,
      status: 'interview',
      intent: 'Quero aprender web',
      generation: 2,
      createdAt: '2026-10-20T12:00:00Z',
      updatedAt: '2026-10-20T12:01:00Z',
      operation: null,
      consultedCurriculum: true,
      batch: {
        id: 'batch-1',
        questions: [
          {
            id: 'q1',
            text: 'O que você quer construir?',
            kind: 'single',
            options: [
              { id: 'o1', text: 'Sites', exclusive: false },
              { id: 'nao-sei', text: 'Não sei', exclusive: true },
            ],
          },
        ],
      },
      answeredBatchCount: 1,
      proposal: null,
      message: null,
      failureCode: null,
    })
    expect(answered).toMatchObject({
      status: 'processing',
      batch: null,
      operation: {
        kind: 'answer',
        startedAt: '2026-10-20T12:02:00Z',
        stage: 'composing',
      },
    })
    expect(restarted).toMatchObject({ status: 'processing', batch: null })
    expect(confirmed).toEqual({ goalId: 'goal-1', replayed: true })
    expect(retried).toMatchObject({
      status: 'proposal',
      operation: { kind: 'start', stage: null },
      proposal: {
        title: 'Aprender web',
        description: 'Do HTML ao React.',
        skills: [{ skillId: 'skill-html', name: 'HTML e CSS', justification: 'Base.' }],
        relations: [{ skillId: 'skill-react', foundationSkillId: 'skill-html' }],
      },
    })

    const failing = {
      get: vi.fn(
        async () =>
          new RestResponse({ statusCode: 409, errorMessage: 'Operação em andamento.' }),
      ),
      delete: vi.fn(async () => new RestResponse({ statusCode: 404 })),
    } as unknown as RestClient
    mocks.intelligenceService.mockImplementation(() => createIntelligenceService(failing))
    expect(await getPlanningSessionServer({ data: { planningId: PLANNING_ID } })).toEqual(
      {
        kind: 'conflict',
        message: 'Operação em andamento.',
      },
    )
    expect(await cancelPlanningServer({ data: { planningId: PLANNING_ID } })).toEqual({
      kind: 'not-found',
    })
  })
})
