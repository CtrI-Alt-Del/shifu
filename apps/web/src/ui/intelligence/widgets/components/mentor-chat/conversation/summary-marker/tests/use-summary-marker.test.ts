import { act, cleanup, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { MentorSummaryMarker } from '@/core/intelligence/mentor-session-summary'
import type { MentorContextValue } from '@/ui/intelligence/contexts/mentor-context/types'
import { useMentorContext } from '@/ui/intelligence/hooks/use-mentor-context'
import { useMentorSessionSummaryQuery } from '../use-mentor-session-summary-query'
import { type SummaryMarkerProps, useSummaryMarker } from '../use-summary-marker'

vi.mock('@/ui/intelligence/hooks/use-mentor-context', () => ({
  useMentorContext: vi.fn(),
}))
vi.mock('../use-mentor-session-summary-query', () => ({
  useMentorSessionSummaryQuery: vi.fn(),
}))

const useMentorContextMock = vi.mocked(useMentorContext)
const useMentorSessionSummaryQueryMock = vi.mocked(useMentorSessionSummaryQuery)
const revealMessageMock = vi.fn()
const refetchSummaryMock = vi.fn()
const MARKER: MentorSummaryMarker = {
  version: 2,
  boundaryMessageId: 'boundary',
  coveredMessageCount: 21,
  completedAt: '2026-10-18T14:00:00Z',
}
const READY: SummaryMarkerProps = { variant: 'ready', marker: MARKER }
const CONTENT = {
  version: 2,
  text: 'Nesta conversa, os assuntos foram range.',
  coveredMessageCount: 21,
  firstMessageId: 'first',
}

type QueryResult = ReturnType<typeof useMentorSessionSummaryQuery>
function mockQuery(overrides: Partial<QueryResult> = {}) {
  useMentorSessionSummaryQueryMock.mockReturnValue({
    summaryContent: CONTENT,
    summaryError: null,
    isLoadingSummary: false,
    refetchSummary: refetchSummaryMock,
    ...overrides,
  } as unknown as QueryResult)
}

describe('useSummaryMarker', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useMentorContextMock.mockReturnValue({
      selectedSessionId: 'session',
      sessionDetail: { messages: { items: [] } },
      revealMessage: revealMessageMock,
    } as unknown as MentorContextValue)
    mockQuery()
  })
  afterEach(() => {
    cleanup()
    document.body.innerHTML = ''
  })

  it('stays closed and does not fetch until the dialog is first opened', () => {
    const { result } = renderHook(() => useSummaryMarker(READY))

    expect(result.current.isOpen).toBe(false)
    expect(useMentorSessionSummaryQueryMock).toHaveBeenLastCalledWith({
      sessionId: 'session',
      version: 2,
      isEnabled: false,
    })

    act(() => result.current.handleOpenChange(true))

    expect(result.current.isOpen).toBe(true)
    expect(useMentorSessionSummaryQueryMock).toHaveBeenLastCalledWith({
      sessionId: 'session',
      version: 2,
      isEnabled: true,
    })

    act(() => result.current.handleOpenChange(false))

    expect(result.current.isOpen).toBe(false)
    expect(useMentorSessionSummaryQueryMock).toHaveBeenLastCalledWith({
      sessionId: 'session',
      version: 2,
      isEnabled: true,
    })
  })

  it('exposes the summary text, loading and error states of the content query', () => {
    const { result, rerender } = renderHook(() => useSummaryMarker(READY))
    expect(result.current.summaryText).toBe(CONTENT.text)
    expect(result.current.hasSummaryError).toBe(false)
    expect(result.current.isLoadingSummary).toBe(false)

    mockQuery({ summaryContent: null, isLoadingSummary: true })
    rerender()
    expect(result.current.summaryText).toBeNull()
    expect(result.current.isLoadingSummary).toBe(true)

    mockQuery({ summaryContent: null, summaryError: new Error('falha') })
    rerender()
    expect(result.current.hasSummaryError).toBe(true)
    expect(result.current.summaryText).toBeNull()
  })

  it('does not scope a summary version for the processing and failed variants', () => {
    renderHook(() => useSummaryMarker({ variant: 'processing' }))
    expect(useMentorSessionSummaryQueryMock).toHaveBeenLastCalledWith({
      sessionId: 'session',
      version: null,
      isEnabled: false,
    })

    renderHook(() => useSummaryMarker({ variant: 'failed' }))
    expect(useMentorSessionSummaryQueryMock).toHaveBeenLastCalledWith({
      sessionId: 'session',
      version: null,
      isEnabled: false,
    })
  })

  it('retries the summary read', () => {
    const { result } = renderHook(() => useSummaryMarker(READY))

    result.current.handleRetry()

    expect(refetchSummaryMock).toHaveBeenCalledOnce()
  })

  it('closes, reveals the first summarized message, scrolls to it and focuses it', async () => {
    revealMessageMock.mockResolvedValue(true)
    const section = document.createElement('section')
    const root = document.createElement('div')
    const target = document.createElement('li')
    target.tabIndex = -1
    target.dataset.messageId = 'first'
    target.scrollIntoView = vi.fn()
    section.append(root, target)
    document.body.append(section)
    const { result } = renderHook(() => useSummaryMarker(READY))
    result.current.rootRef.current = root
    act(() => result.current.handleOpenChange(true))

    await act(() => result.current.handleRevealOriginals())

    expect(revealMessageMock).toHaveBeenCalledWith('first')
    expect(result.current.isOpen).toBe(false)
    expect(target.scrollIntoView).toHaveBeenCalledWith({ block: 'center' })
    expect(target).toHaveFocus()
  })

  it('keeps focus away from the trigger while revealing and restores the default afterwards', async () => {
    revealMessageMock.mockResolvedValue(true)
    const { result } = renderHook(() => useSummaryMarker(READY))
    const preventDefault = vi.fn()
    const beforeReveal = new Event('focus')
    beforeReveal.preventDefault = preventDefault
    result.current.handleCloseAutoFocus(beforeReveal)
    expect(preventDefault).not.toHaveBeenCalled()

    let pendingReveal: Promise<void> = Promise.resolve()
    act(() => {
      pendingReveal = result.current.handleRevealOriginals()
    })
    const duringReveal = new Event('focus')
    duringReveal.preventDefault = preventDefault
    result.current.handleCloseAutoFocus(duringReveal)
    expect(preventDefault).toHaveBeenCalledOnce()
    await act(() => pendingReveal)

    act(() => result.current.handleOpenChange(true))
    const afterReopen = new Event('focus')
    afterReopen.preventDefault = preventDefault
    result.current.handleCloseAutoFocus(afterReopen)
    expect(preventDefault).toHaveBeenCalledOnce()
  })

  it('returns focus to the trigger when the first message cannot be found', async () => {
    revealMessageMock.mockResolvedValue(false)
    const { result } = renderHook(() => useSummaryMarker(READY))
    const trigger = document.createElement('button')
    document.body.append(trigger)
    result.current.triggerRef.current = trigger

    await act(() => result.current.handleRevealOriginals())

    expect(trigger).toHaveFocus()
    expect(result.current.isOpen).toBe(false)
  })

  it('releases the reveal and returns focus to the trigger when the revealed message never renders', async () => {
    vi.useFakeTimers()
    try {
      revealMessageMock.mockResolvedValue(true)
      const { result } = renderHook(() => useSummaryMarker(READY))
      const trigger = document.createElement('button')
      document.body.append(trigger)
      result.current.triggerRef.current = trigger

      await act(() => result.current.handleRevealOriginals())
      expect(trigger).not.toHaveFocus()
      const preventDefault = vi.fn()
      const duringReveal = new Event('focus')
      duringReveal.preventDefault = preventDefault
      result.current.handleCloseAutoFocus(duringReveal)
      expect(preventDefault).toHaveBeenCalledOnce()

      act(() => {
        vi.advanceTimersByTime(3000)
      })

      expect(trigger).toHaveFocus()
      const afterTimeout = new Event('focus')
      afterTimeout.preventDefault = preventDefault
      result.current.handleCloseAutoFocus(afterTimeout)
      expect(preventDefault).toHaveBeenCalledOnce()
      await act(() => result.current.handleRevealOriginals())
      expect(revealMessageMock).toHaveBeenCalledTimes(2)
    } finally {
      vi.useRealTimers()
    }
  })

  it('does not move focus to the trigger once the revealed message took focus', async () => {
    vi.useFakeTimers()
    try {
      revealMessageMock.mockResolvedValue(true)
      const section = document.createElement('section')
      const root = document.createElement('div')
      const target = document.createElement('li')
      target.tabIndex = -1
      target.dataset.messageId = 'first'
      const trigger = document.createElement('button')
      section.append(root, target, trigger)
      document.body.append(section)
      const { result } = renderHook(() => useSummaryMarker(READY))
      result.current.rootRef.current = root
      result.current.triggerRef.current = trigger

      await act(() => result.current.handleRevealOriginals())
      act(() => {
        vi.advanceTimersByTime(5000)
      })

      expect(target).toHaveFocus()
    } finally {
      vi.useRealTimers()
    }
  })

  it('ignores revealing while the summary content is not loaded', async () => {
    mockQuery({ summaryContent: null })
    const { result } = renderHook(() => useSummaryMarker(READY))

    await act(() => result.current.handleRevealOriginals())

    expect(revealMessageMock).not.toHaveBeenCalled()
  })
})
