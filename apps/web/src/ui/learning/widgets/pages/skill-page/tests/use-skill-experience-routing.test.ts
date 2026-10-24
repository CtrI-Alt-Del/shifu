import { createElement, type ReactNode } from 'react'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { RestResponse } from '@/core/shared/responses/rest-response'

import { useSkillExperience } from '../use-skill-experience'

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
const DETAIL = {
  goalId: IDS.goalId,
  skillId: IDS.skillId,
  skillName: 'React',
  skillStatus: 'learning',
  overallResult: 60,
  overallCoverageComplete: true,
  focusCompetencyId: IDS.competencyId,
  focusCompetencyName: 'Componentes',
  competencies: [],
  recommendation: null,
  recommendationGap: null,
  evaluation: null,
}

function setup() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return renderHook(() => useSkillExperience(IDS), {
    wrapper: ({ children }: { children: ReactNode }) =>
      createElement(QueryClientProvider, { client }, children),
  })
}

describe('useSkillExperience routed Skill consumer', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.getCurrentAccess.mockResolvedValue({
      accountId: 'account-1',
      accessToken: 'test-token',
    })
    mocks.get.mockResolvedValue(new RestResponse({ statusCode: 200, body: DETAIL }))
    mocks.post.mockResolvedValue(new RestResponse({ statusCode: 200, body: {} }))
  })
  afterEach(cleanup)

  it('reads the authenticated Skill experience for the selected Goal', async () => {
    const { result } = setup()
    await waitFor(() => expect(result.current.experience?.skillName).toBe('React'))
    expect(mocks.get).toHaveBeenCalledWith(
      `/learning/goals/${IDS.goalId}/skills/${IDS.skillId}`,
      { headers: { Authorization: 'Bearer test-token' } },
    )
  })

  it('keeps a private absence from presenting stale Skill content', async () => {
    mocks.get.mockResolvedValue(new RestResponse({ statusCode: 404 }))
    const { result } = setup()
    await waitFor(() => expect(result.current.isExperienceLoading).toBe(false))
    expect(result.current.experience).toBeNull()
  })

  it('retries the failed evaluation and refreshes the same Skill experience', async () => {
    mocks.get.mockResolvedValue(
      new RestResponse({
        statusCode: 200,
        body: {
          ...DETAIL,
          evaluation: {
            evaluationId: '01J00000000000000000000006',
            status: 'failed',
            attemptId: IDS.attemptId,
            activityId: IDS.activityId,
            competencyId: IDS.competencyId,
          },
        },
      }),
    )
    const { result } = setup()
    await waitFor(() =>
      expect(result.current.experience?.evaluation?.status).toBe('failed'),
    )
    await act(async () => result.current.handleRetryEvaluation())
    expect(mocks.post).toHaveBeenCalledWith(
      `/learning/goals/${IDS.goalId}/skills/${IDS.skillId}/competencies/${IDS.competencyId}/activities/${IDS.activityId}/attempts/${IDS.attemptId}/retry`,
      {},
      { headers: { Authorization: 'Bearer test-token' } },
    )
    expect(mocks.get).toHaveBeenCalledTimes(2)
    expect(result.current.retryFailed).toBe(false)
  })
})
