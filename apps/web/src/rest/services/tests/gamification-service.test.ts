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

describe('GamificationService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('maps every gamification endpoint to its HTTP contract', async () => {
    const overview = { level: 3, families: [] }
    const calendar = { days: [] }
    const history = { totalXp: 160, entries: [] }
    restClientMock.get
      .mockResolvedValueOnce(success(overview))
      .mockResolvedValueOnce(success(calendar))
      .mockResolvedValueOnce(success(history))

    const service = GamificationService(restClient)
    const auth = { headers: { Authorization: 'Bearer token-123' } }

    const achievements = await service.listAchievements('token-123')
    const practiceCalendar = await service.getPracticeCalendar('token-123', 2026, 9)
    const xpHistory = await service.getXpHistory('token-123')

    expect(achievements).toBe(overview)
    expect(practiceCalendar).toBe(calendar)
    expect(xpHistory).toBe(history)
    expect(restClientMock.get).toHaveBeenNthCalledWith(
      1,
      '/gamification/achievements',
      auth,
    )
    expect(restClientMock.get).toHaveBeenNthCalledWith(
      2,
      '/gamification/calendar?year=2026&month=9',
      auth,
    )
    expect(restClientMock.get).toHaveBeenNthCalledWith(
      3,
      '/gamification/xp-history',
      auth,
    )
  })

  it('throws the response error for every endpoint on failure', async () => {
    const error = new Error('unavailable')
    restClientMock.get.mockResolvedValue(failure(error))

    const service = GamificationService(restClient)

    await expect(service.listAchievements('token')).rejects.toBe(error)
    await expect(service.getPracticeCalendar('token', 2026, 9)).rejects.toBe(error)
    await expect(service.getXpHistory('token')).rejects.toBe(error)
  })
})
