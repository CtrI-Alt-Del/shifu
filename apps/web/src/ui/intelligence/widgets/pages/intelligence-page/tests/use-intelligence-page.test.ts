import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ROUTES } from '@/constants/routes'
import { useIntelligencePage } from '../use-intelligence-page'

const mocks = vi.hoisted(() => ({
  navigate: vi.fn(),
  search: {
    session: '01J7T8AC91Z5K8M4JQ8C2D6F0B' as string | undefined,
    message: undefined as string | undefined,
  },
  selectSession: vi.fn(),
  revealMessage: vi.fn(),
  sessionDetail: null as {
    session: { id: string }
    messages: { items: unknown[] }
  } | null,
  startNewConversation: vi.fn(),
  selectedSessionId: null as string | null,
  isValidatingScope: false,
}))

vi.mock('@tanstack/react-router', () => ({
  useNavigate: () => mocks.navigate,
  useSearch: () => mocks.search,
}))
vi.mock('@/ui/intelligence/hooks/use-mentor-context', () => ({
  useMentorContext: () => ({
    selectedSessionId: mocks.selectedSessionId,
    isValidatingScope: mocks.isValidatingScope,
    selectSession: mocks.selectSession,
    startNewConversation: mocks.startNewConversation,
    revealMessage: mocks.revealMessage,
    sessionDetail: mocks.sessionDetail,
  }),
}))

describe('useIntelligencePage', () => {
  afterEach(cleanup)
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.search.session = '01J7T8AC91Z5K8M4JQ8C2D6F0B'
    mocks.search.message = undefined
    mocks.isValidatingScope = false
    mocks.selectedSessionId = null
    mocks.sessionDetail = null
    mocks.selectSession.mockResolvedValue(undefined)
    mocks.revealMessage.mockResolvedValue(true)
  })

  it('loads a session selected in the URL before presenting the page', async () => {
    const { result } = renderHook(() => useIntelligencePage())
    await waitFor(() =>
      expect(mocks.selectSession).toHaveBeenCalledWith(mocks.search.session),
    )
    await waitFor(() => expect(result.current.isPageReady).toBe(true))
  })

  it('is ready on first mount when the shared FAB selection matches the URL', async () => {
    mocks.selectedSessionId = '01J7T8AC91Z5K8M4JQ8C2D6F0B'
    mocks.search.session = mocks.selectedSessionId
    const { result } = renderHook(() => useIntelligencePage())
    await waitFor(() => expect(result.current.isPageReady).toBe(true))
    expect(mocks.selectSession).not.toHaveBeenCalled()
  })

  it('starts a transient new draft when the URL drops its selected session', async () => {
    mocks.search.session = '01J7T8AC91Z5K8M4JQ8C2D6F0B'
    mocks.selectedSessionId = '01J7T8AC91Z5K8M4JQ8C2D6F0B'
    const { rerender } = renderHook(() => useIntelligencePage())
    mocks.search.session = undefined
    rerender()
    await waitFor(() => expect(mocks.startNewConversation).toHaveBeenCalled())
    expect(mocks.navigate).not.toHaveBeenCalledWith({
      to: ROUTES.intelligence,
      search: { session: undefined },
      replace: true,
    })
  })

  it('replaces a stale URL selection with the current context selection', async () => {
    mocks.search.session = undefined
    mocks.selectedSessionId = '01J7T8AC91Z5K8M4JQ8C2D6F0B'
    renderHook(() => useIntelligencePage())
    await waitFor(() =>
      expect(mocks.navigate).toHaveBeenCalledWith({
        to: ROUTES.intelligence,
        search: { session: mocks.selectedSessionId },
        replace: true,
      }),
    )
  })

  it('does not reload when a changing URL already matches the shared context', async () => {
    mocks.search.session = '01J7T8AC91Z5K8M4JQ8C2D6F0B'
    mocks.selectedSessionId = null
    const { rerender } = renderHook(() => useIntelligencePage())
    await waitFor(() =>
      expect(mocks.selectSession).toHaveBeenCalledWith(mocks.search.session),
    )
    mocks.selectedSessionId = '01J7T8AC91Z5K8M4JQ8C2D6F0C'
    mocks.search.session = mocks.selectedSessionId
    rerender()
    await waitFor(() => expect(mocks.selectSession).toHaveBeenCalledOnce())
  })

  it('loads a newly selected URL session after the current route has mounted', async () => {
    mocks.search.session = '01J7T8AC91Z5K8M4JQ8C2D6F0B'
    mocks.selectedSessionId = null
    const { rerender, result } = renderHook(() => useIntelligencePage())
    await waitFor(() =>
      expect(mocks.selectSession).toHaveBeenCalledWith(mocks.search.session),
    )
    mocks.search.session = '01J7T8AC91Z5K8M4JQ8C2D6F0C'
    rerender()
    await waitFor(() => expect(mocks.selectSession).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(result.current.isPageReady).toBe(true))
  })
  it('clears the old route when a selected conversation becomes a new draft', async () => {
    mocks.selectedSessionId = mocks.search.session ?? null
    const { rerender } = renderHook(() => useIntelligencePage())
    mocks.selectedSessionId = null
    rerender()
    await waitFor(() =>
      expect(mocks.navigate).toHaveBeenCalledWith({
        to: ROUTES.intelligence,
        search: { session: undefined },
        replace: true,
      }),
    )
    expect(mocks.selectSession).not.toHaveBeenCalled()
  })

  it('updates the URL for a history selection without reloading the old route', async () => {
    mocks.selectedSessionId = mocks.search.session ?? null
    const { rerender } = renderHook(() => useIntelligencePage())
    mocks.selectedSessionId = '01J7T8AC91Z5K8M4JQ8C2D6F0C'
    rerender()
    await waitFor(() =>
      expect(mocks.navigate).toHaveBeenCalledWith({
        to: ROUTES.intelligence,
        search: { session: mocks.selectedSessionId },
        replace: true,
      }),
    )
    expect(mocks.selectSession).not.toHaveBeenCalled()
  })

  it('keeps a newer deep link loading when an older request finishes', async () => {
    let finishFirst: () => void = () => undefined
    let finishSecond: () => void = () => undefined
    mocks.selectSession
      .mockImplementationOnce(
        () =>
          new Promise<void>((resolve) => {
            finishFirst = resolve
          }),
      )
      .mockImplementationOnce(
        () =>
          new Promise<void>((resolve) => {
            finishSecond = resolve
          }),
      )
    const { rerender, result } = renderHook(() => useIntelligencePage())
    mocks.search.session = '01J7T8AC91Z5K8M4JQ8C2D6F0C'
    rerender()
    expect(result.current.isPageReady).toBe(false)
    await act(async () => finishFirst())
    expect(result.current.isPageReady).toBe(false)
    await act(async () => finishSecond())
    expect(result.current.isPageReady).toBe(true)
    expect(mocks.selectSession).toHaveBeenCalledTimes(2)
  })
  it('waits for initial account scope validation before loading a deep link', async () => {
    mocks.isValidatingScope = true
    const { rerender } = renderHook(() => useIntelligencePage())
    expect(mocks.selectSession).not.toHaveBeenCalled()
    mocks.isValidatingScope = false
    rerender()
    await waitFor(() =>
      expect(mocks.selectSession).toHaveBeenCalledWith(mocks.search.session),
    )
  })

  describe('origin message reveal', () => {
    const SESSION_ID = '01J7T8AC91Z5K8M4JQ8C2D6F0B'
    const MESSAGE_ID = '01J7T8AC91Z5K8M4JQ8C2D6F0C'

    function loadConversation(items: unknown[] = []) {
      mocks.selectedSessionId = SESSION_ID
      mocks.sessionDetail = { session: { id: SESSION_ID }, messages: { items } }
    }

    function renderMessageElement() {
      const element = document.createElement('li')
      element.dataset.messageId = MESSAGE_ID
      element.tabIndex = -1
      element.scrollIntoView = vi.fn()
      document.body.append(element)
      return element
    }

    afterEach(() => {
      document.body.innerHTML = ''
      vi.useRealTimers()
    })

    it('reveals the message of the loaded conversation, focuses it and clears the URL value', async () => {
      loadConversation()
      mocks.search.message = MESSAGE_ID
      const element = renderMessageElement()
      renderHook(() => useIntelligencePage())

      await waitFor(() => expect(element).toHaveFocus())

      expect(mocks.revealMessage).toHaveBeenCalledWith(MESSAGE_ID)
      expect(element.scrollIntoView).toHaveBeenCalledWith({ block: 'center' })
      await waitFor(() =>
        expect(mocks.navigate).toHaveBeenCalledWith({
          to: ROUTES.intelligence,
          search: { session: SESSION_ID, message: undefined },
          replace: true,
        }),
      )
    })

    it('reveals a message only once even when the page rerenders', async () => {
      loadConversation()
      mocks.search.message = MESSAGE_ID
      const element = renderMessageElement()
      const { rerender } = renderHook(() => useIntelligencePage())
      await waitFor(() => expect(element).toHaveFocus())

      rerender()
      rerender()

      expect(mocks.revealMessage).toHaveBeenCalledOnce()
    })

    it('reveals again when the same message is linked again after the URL value was cleared', async () => {
      loadConversation()
      mocks.search.message = MESSAGE_ID
      const element = renderMessageElement()
      const { rerender } = renderHook(() => useIntelligencePage())
      await waitFor(() => expect(element).toHaveFocus())

      mocks.search.message = undefined
      rerender()
      mocks.search.message = MESSAGE_ID
      rerender()

      await waitFor(() => expect(mocks.revealMessage).toHaveBeenCalledTimes(2))
    })

    it('waits until the conversation of the URL is loaded', async () => {
      mocks.search.message = MESSAGE_ID
      mocks.selectedSessionId = null
      const { rerender } = renderHook(() => useIntelligencePage())
      await waitFor(() => expect(mocks.selectSession).toHaveBeenCalled())
      expect(mocks.revealMessage).not.toHaveBeenCalled()

      loadConversation()
      rerender()

      await waitFor(() => expect(mocks.revealMessage).toHaveBeenCalledWith(MESSAGE_ID))
    })

    it('does not reveal while the account scope is still being validated', () => {
      loadConversation()
      mocks.search.message = MESSAGE_ID
      mocks.isValidatingScope = true
      renderHook(() => useIntelligencePage())

      expect(mocks.revealMessage).not.toHaveBeenCalled()
    })

    it('opens the conversation normally when the message no longer exists', async () => {
      loadConversation()
      mocks.search.message = MESSAGE_ID
      mocks.revealMessage.mockResolvedValue(false)
      const element = renderMessageElement()
      renderHook(() => useIntelligencePage())

      await waitFor(() =>
        expect(mocks.navigate).toHaveBeenCalledWith({
          to: ROUTES.intelligence,
          search: { session: SESSION_ID, message: undefined },
          replace: true,
        }),
      )
      expect(element).not.toHaveFocus()
    })

    it('focuses the message when it is rendered after the reveal resolved', async () => {
      loadConversation()
      mocks.search.message = MESSAGE_ID
      const { rerender } = renderHook(() => useIntelligencePage())
      await waitFor(() => expect(mocks.revealMessage).toHaveBeenCalled())
      expect(mocks.navigate).not.toHaveBeenCalledWith(
        expect.objectContaining({ search: { session: SESSION_ID, message: undefined } }),
      )

      const element = renderMessageElement()
      mocks.sessionDetail = {
        session: { id: SESSION_ID },
        messages: { items: [{ id: MESSAGE_ID }] },
      }
      rerender()

      await waitFor(() => expect(element).toHaveFocus())
    })

    it('stops waiting for a message that never renders', async () => {
      vi.useFakeTimers()
      loadConversation()
      mocks.search.message = MESSAGE_ID
      renderHook(() => useIntelligencePage())
      await act(async () => {
        await Promise.resolve()
      })
      expect(mocks.navigate).not.toHaveBeenCalled()

      await act(async () => {
        vi.advanceTimersByTime(3000)
      })

      expect(mocks.navigate).toHaveBeenCalledWith({
        to: ROUTES.intelligence,
        search: { session: SESSION_ID, message: undefined },
        replace: true,
      })
    })

    it('drops the message when a stale selection is replaced and the URL has no session', async () => {
      mocks.search.session = SESSION_ID
      mocks.search.message = MESSAGE_ID
      mocks.selectedSessionId = SESSION_ID
      mocks.sessionDetail = null
      renderHook(() => useIntelligencePage())
      expect(mocks.navigate).not.toHaveBeenCalled()

      cleanup()
      mocks.search.session = undefined
      mocks.selectedSessionId = '01J7T8AC91Z5K8M4JQ8C2D6F0D'
      renderHook(() => useIntelligencePage())

      await waitFor(() =>
        expect(mocks.navigate).toHaveBeenCalledWith({
          to: ROUTES.intelligence,
          search: { session: '01J7T8AC91Z5K8M4JQ8C2D6F0D', message: undefined },
          replace: true,
        }),
      )
    })
  })
})
