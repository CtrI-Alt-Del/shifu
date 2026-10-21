import { createElement, type ReactNode } from 'react'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { RestResponse } from '@/core/shared/responses/rest-response'

import { useSkillPage } from '../use-skill-page'

const mocks = vi.hoisted(() => ({
  getCurrentAccess: vi.fn(),
  get: vi.fn(),
  post: vi.fn(),
  navigate: vi.fn(),
  navigateTo: vi.fn(),
  getGoalDetail: vi.fn(),
}))

vi.mock('@tanstack/react-router', () => ({ useNavigate: () => mocks.navigate }))
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
vi.mock('@/provision/learning/get-goal-detail', () => ({
  getGoalDetail: (input: unknown) => mocks.getGoalDetail(input),
}))
vi.mock('@/ui/shared/hooks/use-navigation', () => ({
  useNavigation: () => ({ navigateTo: mocks.navigateTo, navigateToGoalDetail: vi.fn() }),
}))
vi.mock('@/ui/learning/hooks/use-remove-skill-action', () => ({
  useRemoveSkillAction: () => ({
    isRemovingSkill: false,
    removeSkill: vi.fn(),
    removeSkillError: null,
    resetRemoveSkill: vi.fn(),
  }),
}))

const IDS = {
  goalId: '01J00000000000000000000001',
  skillId: '01J00000000000000000000002',
}
const DIAGNOSTIC = {
  status: 'diagnosing',
  runState: 'requires_entry',
  readyToComplete: false,
  nextCompetencyId: null,
  nextActivityId: null,
  pendingAttemptId: null,
  pendingAttemptStatus: null,
  focusCompetencyId: null,
  competencies: [],
  initialOverallResult: null,
  overallCoverageComplete: false,
  directCompletion: false,
}

function setup() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return renderHook(() => useSkillPage(IDS), {
    wrapper: ({ children }: { children: ReactNode }) =>
      createElement(QueryClientProvider, { client }, children),
  })
}

describe('useSkillPage routed diagnostic start consumer', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.getCurrentAccess.mockResolvedValue({
      accountId: 'account-1',
      accessToken: 'test-token',
    })
    mocks.getGoalDetail.mockResolvedValue({
      kind: 'success',
      detail: { goalId: IDS.goalId, title: 'React', skills: [], relations: [] },
    })
    mocks.get.mockResolvedValue(new RestResponse({ statusCode: 200, body: DIAGNOSTIC }))
    mocks.post.mockResolvedValue(
      new RestResponse({ statusCode: 409, body: { code: 'curriculum_gap' } }),
    )
  })
  afterEach(cleanup)

  it('explains a Curriculum gap when the server rejects automatic diagnostic entry', async () => {
    const { result } = setup()
    await waitFor(() =>
      expect(result.current.startError).toContain('cobertura suficiente'),
    )
    expect(mocks.post).toHaveBeenCalledWith(
      `/learning/goals/${IDS.goalId}/skills/${IDS.skillId}/start`,
      { entry_key: expect.any(String) },
      { headers: { Authorization: 'Bearer test-token' } },
    )
    expect(result.current.hasDiagnosticRun).toBe(false)
    expect(mocks.navigate).not.toHaveBeenCalled()
  })
})
