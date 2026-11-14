import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { createElement, type PropsWithChildren } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AppError } from '@/core/errors/app-error'

import { HOME_GOALS_QUERY_KEY } from '../home-goals-query-key'
import { useHomeGoalsQuery } from '../use-home-goals-query'

const mocks = vi.hoisted(() => ({
  request: new Request('http://shifu.test/'),
  getCurrentAccess: vi.fn(),
  axiosRestClient: vi.fn(),
  learningService: vi.fn(),
  getGoals: vi.fn(),
}))

vi.mock('@tanstack/react-start', () => ({
  createServerFn: () => {
    const builder = {
      middleware: () => builder,
      handler:
        (handler: (input: { context: { requestId: string } }) => Promise<unknown>) =>
        () =>
          handler({ context: { requestId: 'request-1' } }),
    }
    return builder
  },
}))

vi.mock('@/start', () => ({
  serverFunctionTelemetryMiddleware: {},
}))

vi.mock('@tanstack/react-start/server', () => ({
  getRequest: () => mocks.request,
}))

vi.mock('@/constants/server-env', () => ({
  SERVER_ENV: { shifuServerAppUrl: 'http://shifu.test', bffSharedSecret: 'bff-secret' },
}))

vi.mock('@/provision/auth/better-auth/better-auth-provider', () => ({
  getBetterAuthProvider: () => ({ getCurrentAccess: mocks.getCurrentAccess }),
}))

vi.mock('@/rest/axios/axios-rest-client', () => ({
  AxiosRestClient: mocks.axiosRestClient,
}))

vi.mock('@/rest/services/learning-service', () => ({
  LearningService: mocks.learningService,
}))

function renderQuery() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  const wrapper = ({ children }: PropsWithChildren) =>
    createElement(QueryClientProvider, { client: queryClient }, children)
  return { ...renderHook(() => useHomeGoalsQuery(), { wrapper }), queryClient }
}

describe('useHomeGoalsQuery', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mocks.axiosRestClient.mockReturnValue({ restClient: true })
    mocks.learningService.mockReturnValue({ getGoals: mocks.getGoals })
  })

  it('loads the Home goals through the server function under the shared key', async () => {
    mocks.getCurrentAccess.mockResolvedValue({ accessToken: 'access-token' })
    mocks.getGoals.mockResolvedValue([{ id: 'goal-1' }])
    const { result, queryClient } = renderQuery()

    await waitFor(() => expect(result.current.isLoadingGoals).toBe(false))

    expect(result.current.goals).toEqual([{ id: 'goal-1' }])
    expect(mocks.getCurrentAccess).toHaveBeenCalledWith(mocks.request, 'request-1')
    expect(mocks.getGoals).toHaveBeenCalledWith('access-token')
    expect(mocks.axiosRestClient).toHaveBeenCalledWith('http://shifu.test', {
      defaultHeaders: { 'X-Shifu-Bff-Secret': 'bff-secret' },
      withCredentials: false,
      requestId: 'request-1',
      telemetry: undefined,
    })
    expect(queryClient.getQueryData(HOME_GOALS_QUERY_KEY)).toEqual([{ id: 'goal-1' }])
  })

  it('reports an expired session as an error without calling Learning', async () => {
    mocks.getCurrentAccess.mockResolvedValue(null)
    const { result } = renderQuery()

    // The hook retries once before surfacing the error.
    await waitFor(() => expect(result.current.goalsError).toBeInstanceOf(AppError), {
      timeout: 5_000,
    })

    expect(result.current.goals).toEqual([])
    expect(mocks.getGoals).not.toHaveBeenCalled()
  })
})
