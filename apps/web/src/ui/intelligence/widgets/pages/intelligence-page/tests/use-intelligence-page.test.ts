import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ROUTES } from '@/constants/routes'
import { useIntelligencePage } from '../use-intelligence-page'

const mocks = vi.hoisted(() => ({
  navigate: vi.fn(),
  search: { session: '01J7T8AC91Z5K8M4JQ8C2D6F0B' as string | undefined },
  selectSession: vi.fn(),
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
  }),
}))

describe('useIntelligencePage', () => {
  afterEach(cleanup)
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.search.session = '01J7T8AC91Z5K8M4JQ8C2D6F0B'
    mocks.isValidatingScope = false
    mocks.selectedSessionId = null
    mocks.selectSession.mockResolvedValue(undefined)
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
})
