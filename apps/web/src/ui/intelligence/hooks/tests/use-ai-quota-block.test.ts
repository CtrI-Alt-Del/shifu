import { renderHook } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { AiQuotaUsageFaker } from '@/core/intelligence/fakers/ai-quota-usage-faker'

import { useAiQuotaBlock } from '../use-ai-quota-block'
import { useAiQuotaUsageQuery } from '../use-ai-quota-usage-query'

vi.mock('../use-ai-quota-usage-query', () => ({
  useAiQuotaUsageQuery: vi.fn(),
}))

const useAiQuotaUsageQueryMock = vi.mocked(useAiQuotaUsageQuery)

function mockReading(
  usage: ReturnType<typeof useAiQuotaUsageQuery>['aiQuotaUsage'],
  accountId: string | null = 'account-1',
) {
  useAiQuotaUsageQueryMock.mockReturnValue({
    aiQuotaUsage: usage,
    aiQuotaAccountId: accountId,
    isLoadingAiQuotaUsage: false,
    aiQuotaUsageError: null,
    refetchAiQuotaUsage: vi.fn(),
  })
}

describe('useAiQuotaBlock', () => {
  it('does not block below the limit and exposes the account and renewal for the warning', () => {
    mockReading(AiQuotaUsageFaker.fake({ percentage: 42, renewsOn: '2026-12-01' }))

    const { result } = renderHook(() => useAiQuotaBlock())

    expect(result.current).toMatchObject({
      isAiQuotaBlocked: false,
      isAiQuotaNearLimit: false,
      aiQuotaAccountId: 'account-1',
      aiQuotaPercentage: 42,
      aiQuotaRenewsOn: '2026-12-01',
      aiQuotaBlockedRole: 'status',
    })
  })

  it('reports the near-limit warning only while the quota is not blocked', () => {
    mockReading(AiQuotaUsageFaker.fakeNearLimit({ percentage: 85 }))

    const { result } = renderHook(() => useAiQuotaBlock())

    expect(result.current.isAiQuotaNearLimit).toBe(true)
    expect(result.current.isAiQuotaBlocked).toBe(false)
    expect(result.current.aiQuotaPercentage).toBe(85)
  })

  it('blocks when the reading is blocked and gives every surface its own message with the renewal date', () => {
    mockReading(AiQuotaUsageFaker.fakeBlocked({ renewsOn: '2026-12-01' }))

    const { result } = renderHook(() => useAiQuotaBlock())

    expect(result.current.isAiQuotaBlocked).toBe(true)
    expect(result.current.isAiQuotaNearLimit).toBe(false)
    expect(result.current.getAiQuotaBlockedMessage('mentor')).toBe(
      'Sua cota de IA acabou. Novas mensagens e novas tentativas voltam em 1º de dezembro de 2026. Seu histórico continua disponível.',
    )
    expect(result.current.getAiQuotaBlockedMessage('home')).toBe(
      'Sua cota de IA acabou. O planejamento com IA volta em 1º de dezembro de 2026. Você pode criar um Objetivo manualmente agora.',
    )
    expect(result.current.getAiQuotaBlockedMessage('planner-failure')).toContain(
      'Novas tentativas voltam em 1º de dezembro de 2026.',
    )
    expect(result.current.getAiQuotaBlockedMessage('planner-proposal')).toContain(
      'Reiniciar o planejamento volta em 1º de dezembro de 2026.',
    )
  })

  it('lets a refusal on this screen win over a stale reading and announces it as an alert', () => {
    mockReading(AiQuotaUsageFaker.fake({ percentage: 79 }))

    const { result } = renderHook(() => useAiQuotaBlock(true))

    expect(result.current.isAiQuotaBlocked).toBe(true)
    expect(result.current.isAiQuotaNearLimit).toBe(false)
    expect(result.current.aiQuotaBlockedRole).toBe('alert')
  })

  it('keeps AI available and uses the generic message when the reading failed', () => {
    mockReading(null, null)

    const { result } = renderHook(() => useAiQuotaBlock())

    expect(result.current.isAiQuotaBlocked).toBe(false)
    expect(result.current.aiQuotaRenewsOn).toBeNull()
    expect(result.current.aiQuotaPercentage).toBeNull()
    expect(result.current.getAiQuotaBlockedMessage('mentor')).toContain(
      'voltam na próxima renovação',
    )
  })

  it('still explains a refusal without a reading', () => {
    mockReading(null, null)

    const { result } = renderHook(() => useAiQuotaBlock(true))

    expect(result.current.isAiQuotaBlocked).toBe(true)
    expect(result.current.getAiQuotaBlockedMessage('home')).toContain(
      'Sua cota de IA acabou.',
    )
  })
})
