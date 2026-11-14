import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { getOverview, useOverviewQuery } from '../use-overview-query'
import {
  getXpHistory,
  useXpHistoryQuery,
} from '@/ui/gamification/widgets/pages/gamification-xp-history-page/use-xp-history-query'
import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'

const mocks = vi.hoisted(() => ({
  request: null as unknown,
  getCurrentAccess: vi.fn(),
  axiosRestClient: vi.fn(),
  gamificationService: vi.fn(),
  service: {
    getOverview: vi.fn(),
    getXpHistory: vi.fn(),
  },
}))

vi.mock('@tanstack/react-start', () => ({
  createServerFn: () => ({
    handler: (handler: () => Promise<unknown>) => () => handler(),
  }),
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

vi.mock('@/rest/services/gamification-service', () => ({
  GamificationService: mocks.gamificationService,
}))

describe('Gamification server functions', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mocks.request = new Request('http://shifu.test/gamification')
    mocks.getCurrentAccess.mockResolvedValue({ accessToken: 'access-token' })
    mocks.axiosRestClient.mockReturnValue({ restClient: true })
    mocks.gamificationService.mockReturnValue(mocks.service)
  })

  it('returns the overview and the history on success', async () => {
    mocks.service.getOverview.mockResolvedValue({ level: 5 })
    mocks.service.getXpHistory.mockResolvedValue({ entries: [] })

    const overviewResult = await getOverview()
    const historyResult = await getXpHistory()

    expect(overviewResult).toEqual({ kind: 'success', overview: { level: 5 } })
    expect(historyResult).toEqual({ kind: 'success', history: { entries: [] } })
    expect(mocks.axiosRestClient).toHaveBeenCalledWith('http://shifu.test', {
      defaultHeaders: { 'X-Shifu-Bff-Secret': 'bff-secret' },
      withCredentials: false,
    })
    expect(mocks.service.getOverview).toHaveBeenCalledWith('access-token')
    expect(mocks.service.getXpHistory).toHaveBeenCalledWith('access-token')
  })

  it('reports unauthorized when there is no current access', async () => {
    mocks.getCurrentAccess.mockResolvedValue(null)

    expect(await getOverview()).toEqual({ kind: 'unauthorized' })
    expect(await getXpHistory()).toEqual({ kind: 'unauthorized' })
    expect(mocks.service.getOverview).not.toHaveBeenCalled()
  })

  it('maps a rejected AuthError by kind', async () => {
    mocks.service.getOverview.mockRejectedValueOnce(
      new AuthError('authentication-rejected', 'Sua sessão expirou.', {
        statusCode: 401,
      }),
    )
    mocks.service.getOverview.mockRejectedValueOnce(
      new AuthError('unavailable', 'Indisponível.', { statusCode: 503 }),
    )
    mocks.service.getXpHistory.mockRejectedValueOnce(
      new AuthError('authentication-rejected', 'Sua sessão expirou.', {
        statusCode: 401,
      }),
    )
    mocks.service.getXpHistory.mockRejectedValueOnce(
      new AuthError('unavailable', 'Indisponível.', { statusCode: 503 }),
    )

    expect(await getOverview()).toEqual({ kind: 'unauthorized', statusCode: 401 })
    expect(await getOverview()).toEqual({ kind: 'unavailable', statusCode: 503 })
    expect(await getXpHistory()).toEqual({ kind: 'unauthorized', statusCode: 401 })
    expect(await getXpHistory()).toEqual({ kind: 'unavailable', statusCode: 503 })
  })

  it('maps a rejected RestError by status code', async () => {
    mocks.service.getOverview
      .mockRejectedValueOnce(new RestError('Não autorizado.', 401))
      .mockRejectedValueOnce(new RestError('Proibido.', 403))
      .mockRejectedValueOnce(new RestError('Indisponível.', 503))
    mocks.service.getXpHistory
      .mockRejectedValueOnce(new RestError('Não autorizado.', 401))
      .mockRejectedValueOnce(new RestError('Proibido.', 403))
      .mockRejectedValueOnce(new RestError('Indisponível.', 503))

    expect(await getOverview()).toEqual({ kind: 'unauthorized' })
    expect(await getOverview()).toEqual({ kind: 'forbidden' })
    expect(await getOverview()).toEqual({ kind: 'unavailable', statusCode: 503 })
    expect(await getXpHistory()).toEqual({ kind: 'unauthorized' })
    expect(await getXpHistory()).toEqual({ kind: 'forbidden' })
    expect(await getXpHistory()).toEqual({ kind: 'unavailable', statusCode: 503 })
  })

  it('maps an unknown rejection to unavailable', async () => {
    mocks.service.getOverview.mockRejectedValue(new Error('boom'))
    mocks.service.getXpHistory.mockRejectedValue(new Error('boom'))

    expect(await getOverview()).toEqual({ kind: 'unavailable' })
    expect(await getXpHistory()).toEqual({ kind: 'unavailable' })
  })
})

// `useOverviewQuery` and `useXpHistoryQuery` are each a thin `useQuery` wrapper
// over the server function above; widget-testing rules forbid a dedicated query-
// hook test because their behavior is normally proven through the consuming
// widget/page and the route suite. Neither path executes this file's `queryFn`
// closures under Vitest, so this changed file would otherwise be structurally
// unreachable by the repository's per-file coverage gate. This narrow,
// deliberate exception renders the real hook with only the transport mocked
// above, to cover the `queryFn` branches the Playwright route suite already
// proves behaviorally (CI-07) but this Vitest job cannot observe.
describe('Gamification query hooks (queryFn mapping only)', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mocks.request = new Request('http://shifu.test/gamification')
    mocks.getCurrentAccess.mockResolvedValue({ accessToken: 'access-token' })
    mocks.axiosRestClient.mockReturnValue({ restClient: true })
    mocks.gamificationService.mockReturnValue(mocks.service)
  })

  afterEach(() => {
    cleanup()
  })

  function wrapper() {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    return ({ children }: { children: React.ReactNode }) =>
      createElement(QueryClientProvider, { client }, children)
  }

  it('resolves the overview and the history on success', async () => {
    mocks.service.getOverview.mockResolvedValue({ level: 5 })
    mocks.service.getXpHistory.mockResolvedValue({ entries: [] })

    const overview = renderHook(() => useOverviewQuery(), { wrapper: wrapper() })
    const history = renderHook(() => useXpHistoryQuery(), { wrapper: wrapper() })

    await waitFor(() => expect(overview.result.current.overview).toEqual({ level: 5 }))
    await waitFor(() => expect(history.result.current.history).toEqual({ entries: [] }))
  })

  it('throws AuthError when the server function reports unauthorized or forbidden', async () => {
    mocks.getCurrentAccess.mockResolvedValueOnce(null)

    const unauthorized = renderHook(() => useOverviewQuery(), { wrapper: wrapper() })
    await waitFor(() => expect(unauthorized.result.current.overviewError).not.toBeNull())
    expect(unauthorized.result.current.overviewError).toBeInstanceOf(AuthError)

    mocks.service.getOverview.mockRejectedValueOnce(new RestError('Proibido.', 403))
    const forbidden = renderHook(() => useOverviewQuery(), { wrapper: wrapper() })
    await waitFor(() => expect(forbidden.result.current.overviewError).not.toBeNull())
    expect(forbidden.result.current.overviewError).toBeInstanceOf(AuthError)
  })

  it('throws RestError when the server function is unavailable, with and without a status code', async () => {
    mocks.service.getOverview.mockRejectedValueOnce(new Error('boom'))

    const withoutStatus = renderHook(() => useOverviewQuery(), { wrapper: wrapper() })
    await waitFor(() => expect(withoutStatus.result.current.overviewError).not.toBeNull())
    expect(withoutStatus.result.current.overviewError).toBeInstanceOf(RestError)
    expect((withoutStatus.result.current.overviewError as RestError).statusCode).toBe(503)

    mocks.service.getOverview.mockRejectedValueOnce(
      new AuthError('unavailable', 'Indisponível.', { statusCode: 502 }),
    )
    const withStatus = renderHook(() => useOverviewQuery(), { wrapper: wrapper() })
    await waitFor(() => expect(withStatus.result.current.overviewError).not.toBeNull())
    expect((withStatus.result.current.overviewError as RestError).statusCode).toBe(502)
  })

  it('refetches on retry', async () => {
    mocks.service.getOverview.mockResolvedValue({ level: 5 })
    const { result } = renderHook(() => useOverviewQuery(), { wrapper: wrapper() })
    await waitFor(() => expect(result.current.overview).toEqual({ level: 5 }))

    await act(async () => {
      await result.current.refetchOverview()
    })

    expect(mocks.service.getOverview).toHaveBeenCalledTimes(2)
  })

  it('maps the history server function result the same way, by kind and status code', async () => {
    mocks.getCurrentAccess.mockResolvedValueOnce(null)
    const unauthorized = renderHook(() => useXpHistoryQuery(), { wrapper: wrapper() })
    await waitFor(() => expect(unauthorized.result.current.historyError).not.toBeNull())
    expect(unauthorized.result.current.historyError).toBeInstanceOf(AuthError)

    mocks.service.getXpHistory.mockRejectedValueOnce(new Error('boom'))
    const unavailable = renderHook(() => useXpHistoryQuery(), { wrapper: wrapper() })
    await waitFor(() => expect(unavailable.result.current.historyError).not.toBeNull())
    expect((unavailable.result.current.historyError as RestError).statusCode).toBe(503)

    mocks.service.getXpHistory.mockRejectedValueOnce(
      new AuthError('unavailable', 'Indisponível.', { statusCode: 502 }),
    )
    const withStatus = renderHook(() => useXpHistoryQuery(), { wrapper: wrapper() })
    await waitFor(() => expect(withStatus.result.current.historyError).not.toBeNull())
    expect((withStatus.result.current.historyError as RestError).statusCode).toBe(502)
  })
})
