import { cleanup, renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { HTTP_STATUS_CODE } from '@/constants/http-status-code'
import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'

const mocks = vi.hoisted(() => ({
  request: null as unknown,
  getCurrentAccess: vi.fn(),
  axiosRestClient: vi.fn(),
  gamificationService: vi.fn(),
  service: { getXpHistory: vi.fn() },
}))

vi.mock('@tanstack/react-start', () => ({
  createServerFn: () => ({ handler: (fn: () => unknown) => fn }),
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

vi.mock('@/rest/services/gamification-service', () => ({
  GamificationService: mocks.gamificationService,
}))

function createWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children)
}

describe('useXpHistoryQuery', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mocks.request = new Request('http://shifu.test/gamification')
    mocks.axiosRestClient.mockReturnValue({ restClient: true })
    mocks.gamificationService.mockReturnValue(mocks.service)
    mocks.getCurrentAccess.mockResolvedValue({
      accessToken: 'access-token',
      email: 'learner@example.test',
    })
  })

  afterEach(cleanup)

  async function renderQuery() {
    const { useXpHistoryQuery } = await import('../use-xp-history-query')
    const { result } = renderHook(() => useXpHistoryQuery(), {
      wrapper: createWrapper(),
    })
    await waitFor(() => expect(result.current.isLoadingHistory).toBe(false))
    return result
  }

  it('resolves the real history on success', async () => {
    const history = { totalXp: 160, entries: [] }
    mocks.service.getXpHistory.mockResolvedValue(history)

    const result = await renderQuery()

    expect(result.current.history).toEqual(history)
    expect(result.current.historyError).toBeNull()
    expect(mocks.service.getXpHistory).toHaveBeenCalledWith('access-token')
  })

  it('rejects as an authentication error when there is no current access', async () => {
    mocks.getCurrentAccess.mockResolvedValue(null)

    const result = await renderQuery()

    expect(result.current.history).toBeNull()
    expect(result.current.historyError).toBeInstanceOf(AuthError)
  })

  it('rejects as an authentication error when the service rejects the session', async () => {
    mocks.service.getXpHistory.mockRejectedValue(
      new AuthError('authentication-rejected', 'Sua sessão expirou.'),
    )

    const result = await renderQuery()

    expect(result.current.historyError).toBeInstanceOf(AuthError)
  })

  it('rejects as unavailable when the auth provider itself is unavailable', async () => {
    mocks.service.getXpHistory.mockRejectedValue(
      new AuthError('unavailable', 'Serviço indisponível.'),
    )

    const result = await renderQuery()

    expect(result.current.historyError).toBeInstanceOf(RestError)
  })

  it('rejects as an authentication error on a 401 response', async () => {
    mocks.service.getXpHistory.mockRejectedValue(
      new RestError('Não autorizado.', HTTP_STATUS_CODE.unauthorized),
    )

    const result = await renderQuery()

    expect(result.current.historyError).toBeInstanceOf(AuthError)
  })

  it('rejects as an authentication error on a 403 response', async () => {
    mocks.service.getXpHistory.mockRejectedValue(
      new RestError('Acesso negado.', HTTP_STATUS_CODE.forbidden),
    )

    const result = await renderQuery()

    expect(result.current.historyError).toBeInstanceOf(AuthError)
  })

  it('rejects as unavailable on any other REST error status', async () => {
    mocks.service.getXpHistory.mockRejectedValue(
      new RestError('Fora do ar.', HTTP_STATUS_CODE.serviceUnavailable),
    )

    const result = await renderQuery()

    expect(result.current.historyError).toBeInstanceOf(RestError)
  })

  it('rejects as unavailable for an unrecognized error', async () => {
    mocks.service.getXpHistory.mockRejectedValue(new Error('boom'))

    const result = await renderQuery()

    expect(result.current.historyError).toBeInstanceOf(RestError)
  })
})
