import {
  act,
  cleanup,
  fireEvent,
  render,
  renderHook,
  screen,
} from '@testing-library/react'
import { createElement } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { MentorContextValue } from '@/ui/intelligence/contexts/mentor-context/types'
import { useMentorContext } from '@/ui/intelligence/hooks/use-mentor-context'
import { useConversation } from '../use-conversation'

vi.mock('@/ui/intelligence/hooks/use-mentor-context', () => ({
  useMentorContext: vi.fn(),
}))
const useMentorContextMock = vi.mocked(useMentorContext)

describe('useConversation', () => {
  afterEach(cleanup)

  it('requests older messages when the reading position reaches the top', () => {
    const loadOlderMessages = vi.fn()
    useMentorContextMock.mockReturnValue({
      selectedSessionId: 'session-1',
      sessionDetail: {
        session: {
          id: 'session-1',
          title: 'Título',
          createdAt: '',
          updatedAt: '',
          lastActivityAt: '',
        },
        messages: { items: [], nextCursor: 'older-page' },
        pendingLearnerMessageId: null,
      },
      isReadingMessages: false,
      loadOlderMessages,
    } as unknown as MentorContextValue)
    const { result } = renderHook(() => useConversation())
    const element = document.createElement('div')
    Object.defineProperty(element, 'scrollTop', { value: 0, writable: true })
    Object.defineProperty(element, 'scrollHeight', { value: 500 })
    result.current.scrollRef.current = element
    act(() => result.current.handleScroll())
    expect(loadOlderMessages).toHaveBeenCalledOnce()
    element.scrollTop = 100
    act(() => result.current.handleScroll())
    expect(loadOlderMessages).toHaveBeenCalledOnce()
  })

  it('scrolls to the latest message and preserves position when older messages arrive', () => {
    const loadOlderMessages = vi.fn()
    const firstDetail = {
      session: {
        id: 'session-1',
        title: 'Título',
        createdAt: '',
        updatedAt: '',
        lastActivityAt: '',
      },
      messages: {
        items: [
          {
            id: 'new',
            role: 'mentor',
            content: 'Atual',
            createdAt: '2026-10-08T12:01:00Z',
          },
        ],
        nextCursor: 'older',
      },
      pendingLearnerMessageId: null,
    }
    const firstValue = {
      selectedSessionId: 'session-1',
      sessionDetail: firstDetail,
      isReadingMessages: false,
      loadOlderMessages,
    } as unknown as MentorContextValue
    useMentorContextMock.mockReturnValue(firstValue)
    const ScrollHarness = () => {
      const { handleScroll, scrollRef } = useConversation()
      return createElement('div', {
        'data-testid': 'conversation-scroll',
        onScroll: handleScroll,
        ref: (element: HTMLDivElement | null) => {
          if (element && !Object.hasOwn(element, 'scrollHeight')) {
            Object.defineProperty(element, 'scrollHeight', {
              configurable: true,
              value: 500,
            })
          }
          scrollRef.current = element
        },
      })
    }
    const view = render(createElement(ScrollHarness))
    const element = screen.getByTestId('conversation-scroll')
    expect(element.scrollTop).toBe(500)
    element.scrollTop = 0
    fireEvent.scroll(element)
    expect(loadOlderMessages).toHaveBeenCalledOnce()

    const expandedDetail = {
      ...firstDetail,
      messages: {
        items: [
          {
            id: 'old',
            role: 'learner',
            content: 'Anterior',
            createdAt: '2026-10-08T12:00:00Z',
          },
          ...firstDetail.messages.items,
        ],
        nextCursor: null,
      },
    }
    useMentorContextMock.mockReturnValue({
      ...firstValue,
      sessionDetail: expandedDetail,
    } as unknown as MentorContextValue)
    Object.defineProperty(element, 'scrollHeight', { configurable: true, value: 700 })
    view.rerender(createElement(ScrollHarness))
    expect(element.scrollTop).toBe(200)
    view.unmount()
  })

  it('uses the browser scrollTo method when returning to a new draft', () => {
    const scrollTo = vi.fn()
    Object.defineProperty(HTMLElement.prototype, 'scrollTo', {
      configurable: true,
      value: scrollTo,
    })
    useMentorContextMock.mockReturnValue({
      selectedSessionId: null,
      sessionDetail: null,
    } as unknown as MentorContextValue)
    const ScrollHarness = () => {
      const { scrollRef } = useConversation()
      return createElement('div', { ref: scrollRef })
    }
    const view = render(createElement(ScrollHarness))
    expect(scrollTo).toHaveBeenCalledWith({ top: 0 })
    view.unmount()
    Object.defineProperty(HTMLElement.prototype, 'scrollTo', {
      configurable: true,
      value: undefined,
    })
  })
})
