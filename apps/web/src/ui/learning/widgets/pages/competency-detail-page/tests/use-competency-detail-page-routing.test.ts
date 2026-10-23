import { createElement, type ReactNode } from 'react'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { RestResponse } from '@/core/shared/responses/rest-response'

import { useCompetencyDetailPage } from '../use-competency-detail-page'

const mocks = vi.hoisted(() => ({
  getCurrentAccess: vi.fn(),
  get: vi.fn(),
  navigateTo: vi.fn(),
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
  AxiosRestClient: () => ({ get: mocks.get }),
}))
vi.mock('@/ui/shared/hooks/use-navigation', () => ({
  useNavigation: () => ({ navigateTo: mocks.navigateTo }),
}))

const IDS = {
  goalId: '01J00000000000000000000001',
  skillId: '01J00000000000000000000002',
  competencyId: '01J00000000000000000000003',
}
const PATH = `/learning/goals/${IDS.goalId}/skills/${IDS.skillId}/competencies/${IDS.competencyId}`
const DETAIL = {
  availability: 'available',
  goalId: IDS.goalId,
  skillId: IDS.skillId,
  skillName: 'React',
  competencyId: IDS.competencyId,
  competencyName: 'Componentes',
  focusCompetencyId: IDS.competencyId,
  focusCompetencyName: 'Componentes',
}

function setup() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return renderHook(() => useCompetencyDetailPage(IDS), {
    wrapper: ({ children }: { children: ReactNode }) =>
      createElement(QueryClientProvider, { client }, children),
  })
}

describe('useCompetencyDetailPage routed Competency consumer', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.getCurrentAccess.mockResolvedValue({
      accountId: 'account-1',
      accessToken: 'test-token',
    })
    mocks.get.mockResolvedValue(new RestResponse({ statusCode: 200, body: DETAIL }))
  })
  afterEach(cleanup)

  it('loads the Competency within the authenticated Goal and Skill', async () => {
    const { result } = setup()
    await waitFor(() => expect(result.current.detail).toEqual(DETAIL))
    expect(mocks.get).toHaveBeenCalledWith(PATH, {
      headers: { Authorization: 'Bearer test-token' },
    })
  })

  it('keeps HTTP 404 private and does not present the Competency', async () => {
    mocks.get.mockResolvedValue(new RestResponse({ statusCode: 404 }))
    const { result } = setup()
    await waitFor(() => expect(result.current.isPrivateAbsence).toBe(true))
    expect(result.current.detail).toBeNull()
  })

  it('shows a recoverable failure for an unavailable Competency request', async () => {
    mocks.get.mockResolvedValue(new RestResponse({ statusCode: 503 }))
    const { result } = setup()
    await waitFor(() => expect(result.current.isRecoverableError).toBe(true))
    expect(result.current.isPrivateAbsence).toBe(false)
  })

  it('redirects the learner when the server session is absent', async () => {
    mocks.getCurrentAccess.mockResolvedValue(null)
    const { result } = setup()
    await waitFor(() => expect(mocks.navigateTo).toHaveBeenCalledWith('login'))
    expect(result.current.detail).toBeNull()
  })
})
