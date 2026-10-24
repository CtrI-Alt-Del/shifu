import { createElement, type ReactNode } from 'react'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { RestResponse } from '@/core/shared/responses/rest-response'

import { useMaterialPage } from '../use-material-page'

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
  useNavigation: () => ({ navigateTo: mocks.navigateTo, navigateToActivity: vi.fn() }),
}))

const IDS = {
  goalId: '01J00000000000000000000001',
  skillId: '01J00000000000000000000002',
  competencyId: '01J00000000000000000000003',
  materialId: '01J00000000000000000000004',
}
const PATH = `/learning/goals/${IDS.goalId}/skills/${IDS.skillId}/competencies/${IDS.competencyId}/materials/${IDS.materialId}`
const DETAIL = {
  availability: 'available',
  goalId: IDS.goalId,
  skillId: IDS.skillId,
  skillName: 'React',
  competencyId: IDS.competencyId,
  competencyName: 'Componentes',
  materialId: IDS.materialId,
  materialTitle: 'Componentes reutilizáveis',
  content: 'Conteúdo oficial.',
  recommendation: null,
}

function setup() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return renderHook(() => useMaterialPage(IDS), {
    wrapper: ({ children }: { children: ReactNode }) =>
      createElement(QueryClientProvider, { client }, children),
  })
}

describe('useMaterialPage routed material consumer', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.getCurrentAccess.mockResolvedValue({
      accountId: 'account-1',
      accessToken: 'test-token',
    })
    mocks.get.mockResolvedValue(new RestResponse({ statusCode: 200, body: DETAIL }))
  })
  afterEach(cleanup)

  it('loads the material in its full Goal, Skill and Competency context', async () => {
    const { result } = setup()
    await waitFor(() => expect(result.current.detail).toEqual(DETAIL))
    expect(mocks.get).toHaveBeenCalledWith(PATH, {
      headers: { Authorization: 'Bearer test-token' },
    })
    expect(result.current.isRecoverableError).toBe(false)
  })

  it('renders a private absence for HTTP 404 without exposing material content', async () => {
    mocks.get.mockResolvedValue(new RestResponse({ statusCode: 404 }))
    const { result } = setup()
    await waitFor(() => expect(result.current.isPrivateAbsence).toBe(true))
    expect(result.current.detail).toBeNull()
  })

  it('allows recovery after a temporary service failure', async () => {
    mocks.get.mockResolvedValueOnce(new RestResponse({ statusCode: 503 }))
    const { result } = setup()
    await waitFor(() => expect(result.current.isRecoverableError).toBe(true))
    await result.current.handleRetry()
    await waitFor(() => expect(result.current.detail).toEqual(DETAIL))
    expect(mocks.get).toHaveBeenCalledTimes(2)
  })

  it('redirects to sign in when the authenticated server request is rejected', async () => {
    mocks.getCurrentAccess.mockResolvedValue(null)
    const { result } = setup()
    await waitFor(() => expect(mocks.navigateTo).toHaveBeenCalledWith('login'))
    expect(result.current.detail).toBeNull()
  })
})
