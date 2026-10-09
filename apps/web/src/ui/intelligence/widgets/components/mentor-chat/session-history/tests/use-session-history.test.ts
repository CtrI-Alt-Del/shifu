import { cleanup, render, waitFor } from '@testing-library/react'
import { createElement } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { MentorContextValue } from '@/ui/intelligence/contexts/mentor-context/types'
import { useMentorContext } from '@/ui/intelligence/hooks/use-mentor-context'
import { useSessionHistory } from '../use-session-history'

const mocks = vi.hoisted(() => ({ loadMore: vi.fn() }))
vi.mock('@/ui/intelligence/hooks/use-mentor-context', () => ({
  useMentorContext: vi.fn(),
}))
const useMentorContextMock = vi.mocked(useMentorContext)

describe('useSessionHistory', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('automatically loads another list page near the end of history', async () => {
    class MockIntersectionObserver {
      constructor(private callback: IntersectionObserverCallback) {}
      observe() {
        this.callback(
          [{ isIntersecting: true } as IntersectionObserverEntry],
          this as unknown as IntersectionObserver,
        )
      }
      disconnect() {}
      unobserve() {}
      takeRecords() {
        return []
      }
      root = null
      rootMargin = ''
      thresholds = []
    }
    vi.stubGlobal('IntersectionObserver', MockIntersectionObserver)
    const value = {
      loadMoreSessions: mocks.loadMore,
    } as unknown as MentorContextValue
    useMentorContextMock.mockReturnValue(value)
    const Probe = () => {
      const history = useSessionHistory()
      return createElement('li', { ref: history.loadSentinelRef })
    }
    render(createElement(Probe))
    await waitFor(() => expect(mocks.loadMore).toHaveBeenCalledOnce())
  })
})
