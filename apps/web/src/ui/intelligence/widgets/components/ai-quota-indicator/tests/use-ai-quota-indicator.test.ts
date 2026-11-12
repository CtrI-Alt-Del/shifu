import { renderHook } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { AiQuotaUsageFaker } from '@/core/intelligence/fakers/ai-quota-usage-faker'
import { useAiQuotaUsageQuery } from '@/ui/intelligence/hooks/use-ai-quota-usage-query'

import { useAiQuotaIndicator } from '../use-ai-quota-indicator'

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

describe('useAiQuotaIndicator', () => {
  it('stays hidden during the first load', () => {
    useAiQuotaUsageQueryMock.mockReturnValue(createQuery({ isLoadingAiQuotaUsage: true }))

    const { result } = renderHook(() => useAiQuotaIndicator())

    expect(result.current.isVisible).toBe(false)
  })

  it('maps the normal status to a muted sparkles indicator', () => {
    useAiQuotaUsageQueryMock.mockReturnValue(
      createQuery({
        aiQuotaUsage: AiQuotaUsageFaker.fake({ percentage: 42, status: 'normal' }),
      }),
    )

    const { result } = renderHook(() => useAiQuotaIndicator())

    expect(result.current).toEqual({
      isVisible: true,
      text: 'IA · 42%',
      label: 'Uso da IA: 42% da cota mensal',
      iconName: null,
      toneClassName: 'text-muted-foreground',
    })
  })

  it('maps the near-limit status to a warning icon and label', () => {
    useAiQuotaUsageQueryMock.mockReturnValue(
      createQuery({
        aiQuotaUsage: AiQuotaUsageFaker.fakeNearLimit({ percentage: 85 }),
      }),
    )

    const { result } = renderHook(() => useAiQuotaIndicator())

    expect(result.current).toMatchObject({
      text: 'IA · 85%',
      label: 'Uso da IA: 85% da cota mensal, perto do limite',
      iconName: 'triangle-alert',
      toneClassName: 'text-selo-text',
    })
  })

  it('maps the blocked status to a pause icon and the real percentage', () => {
    useAiQuotaUsageQueryMock.mockReturnValue(
      createQuery({
        aiQuotaUsage: AiQuotaUsageFaker.fakeBlocked({ percentage: 130 }),
      }),
    )

    const { result } = renderHook(() => useAiQuotaIndicator())

    expect(result.current).toMatchObject({
      text: 'IA · 130%',
      label: 'Uso da IA: 130% da cota mensal, cota esgotada',
      iconName: 'circle-pause',
      toneClassName: 'text-selo-text',
    })
  })

  it('shows the unavailable state when the reading failed', () => {
    useAiQuotaUsageQueryMock.mockReturnValue(
      createQuery({ aiQuotaUsageError: new Error('down') }),
    )

    const { result } = renderHook(() => useAiQuotaIndicator())

    expect(result.current).toEqual({
      isVisible: true,
      text: 'IA · indisponível',
      label: 'Uso da IA: indisponível no momento',
      iconName: null,
      toneClassName: 'text-muted-foreground',
    })
  })
})
