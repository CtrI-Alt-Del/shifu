import { act, renderHook } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { AiQuotaUsageFaker } from '@/core/intelligence/fakers/ai-quota-usage-faker'
import { useAiQuotaUsageQuery } from '@/ui/intelligence/hooks/use-ai-quota-usage-query'

import { useAiUsagePage } from '../use-ai-usage-page'

vi.mock('@/ui/intelligence/hooks/use-ai-quota-usage-query', () => ({
  useAiQuotaUsageQuery: vi.fn(),
}))

const useAiQuotaUsageQueryMock = vi.mocked(useAiQuotaUsageQuery)

function createQuery(
  overrides: Partial<ReturnType<typeof useAiQuotaUsageQuery>> = {},
): ReturnType<typeof useAiQuotaUsageQuery> {
  return {
    aiQuotaUsage: null,
    aiQuotaAccountId: null,
    isLoadingAiQuotaUsage: false,
    aiQuotaUsageError: null,
    refetchAiQuotaUsage: vi.fn(),
    ...overrides,
  }
}

describe('useAiUsagePage', () => {
  it('reports the loading state while the first reading is pending', () => {
    useAiQuotaUsageQueryMock.mockReturnValue(createQuery({ isLoadingAiQuotaUsage: true }))

    const { result } = renderHook(() => useAiUsagePage())

    expect(result.current.viewState).toBe('loading')
  })

  it('chooses the normal state with the percentage, renewal date and sentence', () => {
    useAiQuotaUsageQueryMock.mockReturnValue(
      createQuery({
        aiQuotaUsage: AiQuotaUsageFaker.fake({
          percentage: 42,
          renewsOn: '2026-12-01',
        }),
      }),
    )

    const { result } = renderHook(() => useAiUsagePage())

    expect(result.current).toMatchObject({
      viewState: 'ready',
      status: 'normal',
      percentage: 42,
      renewalText: 'Renova em 1º de dezembro de 2026',
      statusSentence: 'O Mentor e o planejamento assistido estão disponíveis.',
    })
  })

  it.each([
    [
      'uses the plain number for other days and a lowercase month',
      '2027-03-15',
      'Renova em 15 de março de 2027',
    ],
    [
      'ignores the time part of a full ISO timestamp',
      '2026-01-01T00:00:00Z',
      'Renova em 1º de janeiro de 2026',
    ],
  ])('formats the renewal date: %s', (_name, renewsOn, expected) => {
    useAiQuotaUsageQueryMock.mockReturnValue(
      createQuery({ aiQuotaUsage: AiQuotaUsageFaker.fake({ percentage: 42, renewsOn }) }),
    )

    const { result } = renderHook(() => useAiUsagePage())

    expect(result.current.renewalText).toBe(expected)
  })

  it('chooses the near-limit and blocked sentences', () => {
    useAiQuotaUsageQueryMock.mockReturnValue(
      createQuery({ aiQuotaUsage: AiQuotaUsageFaker.fakeNearLimit({ percentage: 85 }) }),
    )
    const nearLimit = renderHook(() => useAiUsagePage())

    useAiQuotaUsageQueryMock.mockReturnValue(
      createQuery({
        aiQuotaUsage: AiQuotaUsageFaker.fakeBlocked({
          percentage: 100,
          renewsOn: '2026-12-01',
        }),
      }),
    )
    const blocked = renderHook(() => useAiUsagePage())

    expect(nearLimit.result.current).toMatchObject({
      status: 'near_limit',
      statusSentence:
        'Perto do limite. Quando a cota acabar, o Mentor e o planejamento assistido pausam até a renovação.',
    })
    expect(blocked.result.current).toMatchObject({
      status: 'blocked',
      statusSentence:
        'Cota esgotada. O Mentor e o planejamento assistido voltam em 1º de dezembro de 2026. Seus Objetivos e Atividades continuam disponíveis.',
    })
  })

  it('chooses the unavailable state when the reading failed and retries it', async () => {
    const refetchAiQuotaUsage = vi.fn().mockResolvedValue(undefined)
    useAiQuotaUsageQueryMock.mockReturnValue(
      createQuery({ aiQuotaUsageError: new Error('down'), refetchAiQuotaUsage }),
    )

    const { result } = renderHook(() => useAiUsagePage())

    expect(result.current).toMatchObject({
      viewState: 'unavailable',
      status: null,
      renewalText: '',
      statusSentence: '',
    })

    await act(() => result.current.handleRetry())

    expect(refetchAiQuotaUsage).toHaveBeenCalledOnce()
  })
})
