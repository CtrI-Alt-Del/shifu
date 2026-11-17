import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useAiQuotaWarningCard } from '../use-ai-quota-warning-card'

const NOVEMBER_KEY = 'shifu:ai-quota-warning-dismissed:account-1:2026-11'

describe('useAiQuotaWarningCard', () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('builds the warning message from the percentage and the renewal date', () => {
    const { result } = renderHook(() =>
      useAiQuotaWarningCard({
        accountId: 'account-1',
        percentage: 85,
        renewsOn: '2026-12-01',
      }),
    )

    expect(result.current.message).toBe(
      'Você já usou 85% da sua cota de IA deste mês. Quando ela acabar, o Mentor e o planejamento assistido pausam até 1º de dezembro de 2026.',
    )
    expect(result.current.isDismissed).toBe(false)
  })

  it('persists the dismissal under the account and the month before the renewal', () => {
    const { result } = renderHook(() =>
      useAiQuotaWarningCard({
        accountId: 'account-1',
        percentage: 85,
        renewsOn: '2026-12-01',
      }),
    )

    act(() => result.current.handleDismiss())

    expect(result.current.isDismissed).toBe(true)
    expect(window.localStorage.getItem(NOVEMBER_KEY)).not.toBeNull()
  })

  it('stays dismissed after a reload of the same account and month', () => {
    window.localStorage.setItem(NOVEMBER_KEY, '1')

    const { result } = renderHook(() =>
      useAiQuotaWarningCard({
        accountId: 'account-1',
        percentage: 85,
        renewsOn: '2026-12-01',
      }),
    )

    expect(result.current.isDismissed).toBe(true)
  })

  it('shows the warning again when the month key is missing, for another account or in a new month', () => {
    window.localStorage.setItem(NOVEMBER_KEY, '1')

    const otherAccount = renderHook(() =>
      useAiQuotaWarningCard({
        accountId: 'account-2',
        percentage: 85,
        renewsOn: '2026-12-01',
      }),
    )
    const nextMonth = renderHook(() =>
      useAiQuotaWarningCard({
        accountId: 'account-1',
        percentage: 85,
        renewsOn: '2027-01-01',
      }),
    )
    window.localStorage.removeItem(NOVEMBER_KEY)
    const keyRemoved = renderHook(() =>
      useAiQuotaWarningCard({
        accountId: 'account-1',
        percentage: 85,
        renewsOn: '2026-12-01',
      }),
    )

    expect(otherAccount.result.current.isDismissed).toBe(false)
    expect(nextMonth.result.current.isDismissed).toBe(false)
    expect(keyRemoved.result.current.isDismissed).toBe(false)
  })

  it('shows the warning when reading the dismissal fails', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('storage blocked')
    })

    const { result } = renderHook(() =>
      useAiQuotaWarningCard({
        accountId: 'account-1',
        percentage: 85,
        renewsOn: '2026-12-01',
      }),
    )

    expect(result.current.isDismissed).toBe(false)
  })

  it('hides the warning for the current session only when writing the dismissal fails', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('quota exceeded')
    })
    const { result, unmount } = renderHook(() =>
      useAiQuotaWarningCard({
        accountId: 'account-1',
        percentage: 85,
        renewsOn: '2026-12-01',
      }),
    )

    act(() => result.current.handleDismiss())

    expect(result.current.isDismissed).toBe(true)
    expect(window.localStorage.getItem(NOVEMBER_KEY)).toBeNull()

    unmount()
    const afterReload = renderHook(() =>
      useAiQuotaWarningCard({
        accountId: 'account-1',
        percentage: 85,
        renewsOn: '2026-12-01',
      }),
    )

    expect(afterReload.result.current.isDismissed).toBe(false)
  })
})
