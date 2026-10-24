import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { RestClient } from '@/core/shared/interfaces/rest-client'
import { GamificationService } from '../gamification-service'

const restClientMock = {
  delete: vi.fn(),
  get: vi.fn(),
  getFile: vi.fn(),
  patch: vi.fn(),
  post: vi.fn(),
  postFormData: vi.fn(),
  put: vi.fn(),
}

const restClient = restClientMock as unknown as RestClient
const ACCESS_TOKEN = 'token-123'
const AUTH_HEADERS = {
  headers: { Authorization: ['Bearer', ACCESS_TOKEN].join(' ') },
}

const success = (body: unknown) => ({
  isFailure: false,
  body,
  throwError: vi.fn(),
})
const failure = (error: Error) => ({
  isFailure: true,
  body: undefined,
  throwError: () => {
    throw error
  },
})

describe('GamificationService REST transport', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('maps every gamification read to its HTTP contract and domain value', async () => {
    const overview = { level: 5 }
    const achievements = { level: 5 }
    const calendar = { month: 10 }
    const history = { entries: [] }
    const reward = { state: 'granted', additionalXp: 6 }
    restClientMock.get
      .mockResolvedValueOnce(success(overview))
      .mockResolvedValueOnce(success(achievements))
      .mockResolvedValueOnce(success(calendar))
      .mockResolvedValueOnce(success(history))
      .mockResolvedValueOnce(success(reward))

    const service = GamificationService(restClient)
    const overviewResult = await service.getOverview(ACCESS_TOKEN)
    const achievementsResult = await service.listAchievements(ACCESS_TOKEN)
    const calendarResult = await service.getPracticeCalendar(ACCESS_TOKEN, 2026, 10)
    const historyResult = await service.getXpHistory(ACCESS_TOKEN)
    const rewardResult = await service.getActivityXpReward(
      ACCESS_TOKEN,
      'activity-1',
      'attempt-1',
    )

    expect(overviewResult).toBe(overview)
    expect(achievementsResult).toBe(achievements)
    expect(calendarResult).toBe(calendar)
    expect(historyResult).toBe(history)
    expect(rewardResult).toBe(reward)
    expect(restClientMock.get).toHaveBeenNthCalledWith(
      1,
      '/gamification/overview',
      AUTH_HEADERS,
    )
    expect(restClientMock.get).toHaveBeenNthCalledWith(
      2,
      '/gamification/achievements',
      AUTH_HEADERS,
    )
    expect(restClientMock.get).toHaveBeenNthCalledWith(
      3,
      '/gamification/calendar?year=2026&month=10',
      AUTH_HEADERS,
    )
    expect(restClientMock.get).toHaveBeenNthCalledWith(
      4,
      '/gamification/xp-history',
      AUTH_HEADERS,
    )
    expect(restClientMock.get).toHaveBeenNthCalledWith(
      5,
      '/gamification/activities/activity-1/attempts/attempt-1/xp-reward',
      AUTH_HEADERS,
    )
  })

  it('propagates failed REST responses from every gamification read', async () => {
    const error = new Error('request failed')
    restClientMock.get.mockResolvedValue(failure(error))
    const service = GamificationService(restClient)

    await expect(service.getOverview(ACCESS_TOKEN)).rejects.toBe(error)
    await expect(service.listAchievements(ACCESS_TOKEN)).rejects.toBe(error)
    await expect(service.getPracticeCalendar(ACCESS_TOKEN, 2026, 10)).rejects.toBe(error)
    await expect(service.getXpHistory(ACCESS_TOKEN)).rejects.toBe(error)
    await expect(
      service.getActivityXpReward(ACCESS_TOKEN, 'activity-1', 'attempt-1'),
    ).rejects.toBe(error)
  })
})
