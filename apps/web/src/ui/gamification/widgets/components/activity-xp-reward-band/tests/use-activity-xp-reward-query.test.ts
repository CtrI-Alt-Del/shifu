import { renderHook } from '@testing-library/react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import type { ActivityXpReward } from '@/core/gamification/activity-xp-reward'

import {
  getActivityXpReward,
  MAX_POLL_ATTEMPTS,
  POLL_INTERVAL_MS,
  useActivityXpRewardQuery,
} from '../use-activity-xp-reward-query'

const mocks = vi.hoisted(() => ({
  request: null as unknown,
  getCurrentAccess: vi.fn(),
  axiosRestClient: vi.fn(),
  gamificationService: vi.fn(),
  service: { getActivityXpReward: vi.fn() },
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
vi.mock('@tanstack/react-query', () => ({
  useQuery: vi.fn(),
  useQueryClient: vi.fn(),
}))

const useQueryMock = vi.mocked(useQuery)
const useQueryClientMock = vi.mocked(useQueryClient)

const ACTIVITY_ID = 'activity-1'
const ATTEMPT_ID = 'attempt-1'

const reward: ActivityXpReward = {
  activityId: ACTIVITY_ID,
  attemptId: ATTEMPT_ID,
  state: 'granted',
  additionalXp: 6,
  grantedXp: 6,
  maximumXp: 10,
}

describe('getActivityXpReward', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mocks.request = new Request('http://shifu.test/xp-reward')
    mocks.getCurrentAccess.mockResolvedValue({ accessToken: 'access-token' })
    mocks.axiosRestClient.mockReturnValue({ restClient: true })
    mocks.gamificationService.mockReturnValue(mocks.service)
  })

  it('returns the reward on success', async () => {
    mocks.service.getActivityXpReward.mockResolvedValue(reward)

    const result = await getActivityXpReward({
      data: { activityId: ACTIVITY_ID, attemptId: ATTEMPT_ID },
    })

    expect(result).toEqual({ kind: 'success', reward })
    expect(mocks.axiosRestClient).toHaveBeenCalledWith('http://shifu.test', {
      withCredentials: false,
    })
    expect(mocks.service.getActivityXpReward).toHaveBeenCalledWith(
      'access-token',
      ACTIVITY_ID,
      ATTEMPT_ID,
    )
  })

  it('reports unauthorized when there is no current access', async () => {
    mocks.getCurrentAccess.mockResolvedValue(null)

    const result = await getActivityXpReward({
      data: { activityId: ACTIVITY_ID, attemptId: ATTEMPT_ID },
    })

    expect(result).toEqual({ kind: 'unauthorized' })
    expect(mocks.service.getActivityXpReward).not.toHaveBeenCalled()
  })

  it('maps a rejected AuthError to unauthorized', async () => {
    mocks.service.getActivityXpReward.mockRejectedValue(
      new AuthError('authentication-rejected', 'Sua sessão expirou.', {
        statusCode: 401,
      }),
    )

    const result = await getActivityXpReward({
      data: { activityId: ACTIVITY_ID, attemptId: ATTEMPT_ID },
    })

    expect(result).toEqual({ kind: 'unauthorized', statusCode: 401 })
  })

  it('maps any other AuthError kind to unavailable', async () => {
    mocks.service.getActivityXpReward.mockRejectedValue(
      new AuthError('unavailable', 'Indisponível.', { statusCode: 503 }),
    )

    const result = await getActivityXpReward({
      data: { activityId: ACTIVITY_ID, attemptId: ATTEMPT_ID },
    })

    expect(result).toEqual({ kind: 'unavailable', statusCode: 503 })
  })

  it('maps a RestError with an unauthorized status to unauthorized', async () => {
    mocks.service.getActivityXpReward.mockRejectedValue(new RestError('Sem acesso.', 401))

    const result = await getActivityXpReward({
      data: { activityId: ACTIVITY_ID, attemptId: ATTEMPT_ID },
    })

    expect(result).toEqual({ kind: 'unauthorized' })
  })

  it('maps a RestError with a not-found status to not-found', async () => {
    mocks.service.getActivityXpReward.mockRejectedValue(
      new RestError('Tentativa não encontrada.', 404),
    )

    const result = await getActivityXpReward({
      data: { activityId: ACTIVITY_ID, attemptId: ATTEMPT_ID },
    })

    expect(result).toEqual({ kind: 'not-found' })
  })

  it('maps any other RestError status to unavailable', async () => {
    mocks.service.getActivityXpReward.mockRejectedValue(
      new RestError('Indisponível.', 503),
    )

    const result = await getActivityXpReward({
      data: { activityId: ACTIVITY_ID, attemptId: ATTEMPT_ID },
    })

    expect(result).toEqual({ kind: 'unavailable', statusCode: 503 })
  })

  it('maps an unexpected error to unavailable without a status code', async () => {
    mocks.service.getActivityXpReward.mockRejectedValue(new Error('boom'))

    const result = await getActivityXpReward({
      data: { activityId: ACTIVITY_ID, attemptId: ATTEMPT_ID },
    })

    expect(result).toEqual({ kind: 'unavailable' })
  })
})

describe('useActivityXpRewardQuery', () => {
  const getQueryStateMock = vi.fn()

  beforeEach(() => {
    vi.resetAllMocks()
    mocks.request = new Request('http://shifu.test/xp-reward')
    mocks.getCurrentAccess.mockResolvedValue({ accessToken: 'access-token' })
    mocks.axiosRestClient.mockReturnValue({ restClient: true })
    mocks.gamificationService.mockReturnValue(mocks.service)
    getQueryStateMock.mockReturnValue({ dataUpdateCount: 2 })
    useQueryClientMock.mockReturnValue({
      getQueryState: getQueryStateMock,
    } as never)
    useQueryMock.mockReturnValue({
      data: undefined,
      error: null,
      isPending: true,
    } as never)
  })

  it('scopes the query key to the activity and attempt and requests the reward via the server function', async () => {
    mocks.service.getActivityXpReward.mockResolvedValue(reward)

    renderHook(() => useActivityXpRewardQuery(ACTIVITY_ID, ATTEMPT_ID))

    const options = useQueryMock.mock.calls[0]?.[0]
    expect(options?.queryKey).toEqual([
      'gamification',
      'activity-xp-reward',
      ACTIVITY_ID,
      ATTEMPT_ID,
    ])
    expect(options?.retry).toBe(false)

    const queryFn = options?.queryFn as () => Promise<ActivityXpReward>
    await expect(queryFn()).resolves.toEqual(reward)
  })

  it('throws a RestError when the server function reports a failure', async () => {
    mocks.getCurrentAccess.mockResolvedValue(null)

    renderHook(() => useActivityXpRewardQuery(ACTIVITY_ID, ATTEMPT_ID))

    const queryFn = useQueryMock.mock.calls[0]?.[0]?.queryFn as () => Promise<unknown>
    await expect(queryFn()).rejects.toThrow(RestError)
  })

  it('keeps polling while the reward is pending and under the attempt limit', () => {
    renderHook(() => useActivityXpRewardQuery(ACTIVITY_ID, ATTEMPT_ID))

    const refetchInterval = useQueryMock.mock.calls[0]?.[0]?.refetchInterval as (
      query: unknown,
    ) => number | false

    expect(
      refetchInterval({ state: { data: { state: 'pending' }, dataUpdateCount: 0 } }),
    ).toBe(POLL_INTERVAL_MS)
    expect(
      refetchInterval({
        state: { data: { state: 'pending' }, dataUpdateCount: MAX_POLL_ATTEMPTS },
      }),
    ).toBe(false)
    expect(
      refetchInterval({ state: { data: { state: 'granted' }, dataUpdateCount: 0 } }),
    ).toBe(false)
    expect(refetchInterval({ state: { data: undefined, dataUpdateCount: 0 } })).toBe(
      false,
    )
  })

  it('derives the reward, the error, the loading flag, and the poll attempts', () => {
    useQueryMock.mockReturnValue({
      data: reward,
      error: null,
      isPending: false,
    } as never)

    const { result } = renderHook(() => useActivityXpRewardQuery(ACTIVITY_ID, ATTEMPT_ID))

    expect(result.current.reward).toBe(reward)
    expect(result.current.rewardError).toBeNull()
    expect(result.current.isLoadingReward).toBe(false)
    expect(result.current.pollAttempts).toBe(2)
  })

  it('falls back to a null reward, a null error, and zero poll attempts', () => {
    getQueryStateMock.mockReturnValue(undefined)
    useQueryMock.mockReturnValue({
      data: undefined,
      error: undefined,
      isPending: true,
    } as never)

    const { result } = renderHook(() => useActivityXpRewardQuery(ACTIVITY_ID, ATTEMPT_ID))

    expect(result.current.reward).toBeNull()
    expect(result.current.rewardError).toBeNull()
    expect(result.current.pollAttempts).toBe(0)
  })
})
