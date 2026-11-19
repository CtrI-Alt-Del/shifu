import { renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { ActivityXpReward } from '@/core/gamification/activity-xp-reward'

import { createQueryClientWrapper } from '@/ui/gamification/tests/streak-reminder-transport-support'

import { useActivityXpRewardBand } from '../use-activity-xp-reward-band'
import {
  MAX_POLL_ATTEMPTS,
  useActivityXpRewardQuery,
} from '../use-activity-xp-reward-query'

vi.mock('../use-activity-xp-reward-query', async () => {
  const actual = await vi.importActual<typeof import('../use-activity-xp-reward-query')>(
    '../use-activity-xp-reward-query',
  )
  return { ...actual, useActivityXpRewardQuery: vi.fn() }
})

const useActivityXpRewardQueryMock = vi.mocked(useActivityXpRewardQuery)

const ACTIVITY_ID = 'activity-1'
const ATTEMPT_ID = 'attempt-1'

function mockQuery(overrides: Partial<ReturnType<typeof useActivityXpRewardQuery>> = {}) {
  useActivityXpRewardQueryMock.mockReturnValue({
    reward: null,
    rewardError: null,
    isLoadingReward: true,
    pollAttempts: 0,
    ...overrides,
  })
}

function reward(overrides: Partial<ActivityXpReward> = {}): ActivityXpReward {
  return {
    activityId: ACTIVITY_ID,
    attemptId: ATTEMPT_ID,
    state: 'pending',
    additionalXp: 0,
    grantedXp: 0,
    maximumXp: null,
    ...overrides,
  }
}

describe('useActivityXpRewardBand', () => {
  beforeEach(() => mockQuery())

  it('reports pending while the query has not resolved yet', () => {
    const { result } = renderHook(
      () => useActivityXpRewardBand(ACTIVITY_ID, ATTEMPT_ID),
      {
        wrapper: createQueryClientWrapper().wrapper,
      },
    )

    expect(result.current).toEqual({ status: 'pending' })
  })

  it('reports pending while the server answers pending, within the budget', () => {
    mockQuery({
      reward: reward({ state: 'pending' }),
      isLoadingReward: false,
      pollAttempts: MAX_POLL_ATTEMPTS - 1,
    })

    const { result } = renderHook(
      () => useActivityXpRewardBand(ACTIVITY_ID, ATTEMPT_ID),
      {
        wrapper: createQueryClientWrapper().wrapper,
      },
    )

    expect(result.current).toEqual({ status: 'pending' })
  })

  it('stops asking and reports unavailable once the poll budget is spent', () => {
    mockQuery({
      reward: reward({ state: 'pending' }),
      isLoadingReward: false,
      pollAttempts: MAX_POLL_ATTEMPTS,
    })

    const { result } = renderHook(
      () => useActivityXpRewardBand(ACTIVITY_ID, ATTEMPT_ID),
      {
        wrapper: createQueryClientWrapper().wrapper,
      },
    )

    expect(result.current).toEqual({ status: 'unavailable' })
  })

  it('reports granted with the amounts once the server confirms a grant', () => {
    mockQuery({
      reward: reward({
        state: 'granted',
        additionalXp: 6,
        grantedXp: 6,
        maximumXp: 10,
      }),
      isLoadingReward: false,
    })

    const { result } = renderHook(
      () => useActivityXpRewardBand(ACTIVITY_ID, ATTEMPT_ID),
      {
        wrapper: createQueryClientWrapper().wrapper,
      },
    )

    expect(result.current).toEqual({
      status: 'granted',
      additionalXp: 6,
      grantedXp: 6,
      maximumXp: 10,
    })
  })

  it('reports no-additional for a zero recognition', () => {
    mockQuery({
      reward: reward({ state: 'no-additional', grantedXp: 10, maximumXp: 10 }),
      isLoadingReward: false,
    })

    const { result } = renderHook(
      () => useActivityXpRewardBand(ACTIVITY_ID, ATTEMPT_ID),
      {
        wrapper: createQueryClientWrapper().wrapper,
      },
    )

    expect(result.current).toEqual({
      status: 'no-additional',
      grantedXp: 10,
      maximumXp: 10,
    })
  })

  it('reports unavailable when the query rejects', () => {
    mockQuery({ rewardError: new Error('unavailable'), isLoadingReward: false })

    const { result } = renderHook(
      () => useActivityXpRewardBand(ACTIVITY_ID, ATTEMPT_ID),
      {
        wrapper: createQueryClientWrapper().wrapper,
      },
    )

    expect(result.current).toEqual({ status: 'unavailable' })
  })

  describe('streak reminder refresh', () => {
    function renderWithClient() {
      const { client, wrapper } = createQueryClientWrapper()
      const invalidateQueriesSpy = vi.spyOn(client, 'invalidateQueries')
      const rendered = renderHook(
        () => useActivityXpRewardBand(ACTIVITY_ID, ATTEMPT_ID),
        {
          wrapper,
        },
      )
      return { ...rendered, invalidateQueriesSpy }
    }

    it('does not refresh the invite state while the reward is pending', () => {
      const { invalidateQueriesSpy } = renderWithClient()

      expect(invalidateQueriesSpy).not.toHaveBeenCalled()
    })

    it.each([
      [
        'granted',
        { state: 'granted', additionalXp: 6, grantedXp: 6, maximumXp: 10 } as const,
      ],
      [
        'no-additional',
        { state: 'no-additional', grantedXp: 10, maximumXp: 10 } as const,
      ],
    ])(
      'refreshes the invite state once when the reward leaves pending as %s',
      (_status, settled) => {
        const { rerender, invalidateQueriesSpy } = renderWithClient()

        mockQuery({ reward: reward(settled), isLoadingReward: false })
        rerender()
        rerender()

        expect(invalidateQueriesSpy).toHaveBeenCalledOnce()
        expect(invalidateQueriesSpy).toHaveBeenCalledWith({
          queryKey: ['gamification', 'streak-reminder'],
        })
      },
    )

    it('refreshes the invite state when the pending reward becomes unavailable', () => {
      const { rerender, invalidateQueriesSpy } = renderWithClient()

      mockQuery({ rewardError: new Error('unavailable'), isLoadingReward: false })
      rerender()

      expect(invalidateQueriesSpy).toHaveBeenCalledOnce()
    })

    it('does not refresh the invite state when the reward was already settled', () => {
      mockQuery({
        reward: reward({ state: 'no-additional', grantedXp: 10, maximumXp: 10 }),
        isLoadingReward: false,
      })

      const { invalidateQueriesSpy } = renderWithClient()

      expect(invalidateQueriesSpy).not.toHaveBeenCalled()
    })
  })
})
