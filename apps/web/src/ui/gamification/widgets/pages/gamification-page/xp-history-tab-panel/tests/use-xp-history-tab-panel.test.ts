import { renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AuthError } from '@/core/errors/auth-error'
import type { XpHistory } from '@/core/gamification/xp-history'

import { useXpHistoryTabPanel } from '../use-xp-history-tab-panel'
import { useXpHistoryQuery } from '../use-xp-history-query'

vi.mock('../use-xp-history-query', () => ({ useXpHistoryQuery: vi.fn() }))

const useXpHistoryQueryMock = vi.mocked(useXpHistoryQuery)

const history: XpHistory = {
  totalXp: 110,
  entries: [
    {
      id: 'grant-1',
      amount: 60,
      source: 'diagnosis',
      title: 'Lógica de programação',
      detail: 'Diagnóstico concluído',
      occurredAt: '2026-09-11T12:00:00Z',
      grantedAt: '2026-09-13T12:00:00Z',
    },
    {
      id: 'grant-2',
      amount: 50,
      source: 'competency-mastery',
      title: 'Condicionais',
      detail: 'Primeiro domínio de Competência',
      occurredAt: '2026-09-05T12:00:00Z',
      grantedAt: '2026-09-05T12:00:00Z',
    },
  ],
}

function mockQuery(overrides: Partial<ReturnType<typeof useXpHistoryQuery>> = {}) {
  const refetchHistory = vi.fn()
  useXpHistoryQueryMock.mockReturnValue({
    history,
    historyError: null,
    isLoadingHistory: false,
    isFetchingHistory: false,
    refetchHistory,
    ...overrides,
  } as unknown as ReturnType<typeof useXpHistoryQuery>)
  return refetchHistory
}

describe('useXpHistoryTabPanel', () => {
  beforeEach(() => mockQuery())

  it('reports the loading state while the query is pending', () => {
    mockQuery({ history: null, isLoadingHistory: true, isFetchingHistory: true })

    const { result } = renderHook(() => useXpHistoryTabPanel())

    expect(result.current.state).toBe('loading')
    expect(result.current.entries).toEqual([])
    expect(result.current.totalXp).toBe(0)
    // A first load is not a retry.
    expect(result.current.isRetrying).toBe(false)
  })

  it('exposes the entries and the total on success', () => {
    const { result } = renderHook(() => useXpHistoryTabPanel())

    expect(result.current.state).toBe('success')
    expect(result.current.entries).toHaveLength(2)
    expect(result.current.entries[0].id).toBe('grant-1')
    expect(result.current.entries[1].id).toBe('grant-2')
    expect(result.current.totalXp).toBe(110)
  })

  it('reports the empty state for a successful response with no records', () => {
    mockQuery({ history: { totalXp: 0, entries: [] } })

    const { result } = renderHook(() => useXpHistoryTabPanel())

    expect(result.current.state).toBe('empty')
    expect(result.current.entries).toEqual([])
    expect(result.current.totalXp).toBe(0)
  })

  it('reports the error state when the query rejects', () => {
    mockQuery({
      history: null,
      historyError: new AuthError('authentication-rejected', 'Sua sessão expirou.'),
    })

    const { result } = renderHook(() => useXpHistoryTabPanel())

    expect(result.current.state).toBe('error')
    expect(result.current.entries).toEqual([])
  })

  it('reports the error state when the query resolves without a history', () => {
    mockQuery({ history: null })

    const { result } = renderHook(() => useXpHistoryTabPanel())

    expect(result.current.state).toBe('error')
  })

  it('marks a refetch of an already-loaded query as a retry', () => {
    mockQuery({ isFetchingHistory: true })

    const { result } = renderHook(() => useXpHistoryTabPanel())

    expect(result.current.isRetrying).toBe(true)
  })

  it('refetches the history on retry', () => {
    const refetchHistory = mockQuery()

    const { result } = renderHook(() => useXpHistoryTabPanel())
    result.current.handleRetry()

    expect(refetchHistory).toHaveBeenCalledOnce()
  })
})
