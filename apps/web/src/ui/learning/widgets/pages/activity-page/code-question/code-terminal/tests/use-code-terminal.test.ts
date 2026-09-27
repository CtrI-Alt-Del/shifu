import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type {
  CodePracticeEvent,
  CodePracticeRunner,
} from '@/core/learning/code-practice-runner'
import { useCodeTerminal } from '../use-code-terminal'

const fitMock = vi.hoisted(() => vi.fn())
const onDataMock = vi.hoisted(() => vi.fn())

vi.mock('@xterm/xterm', () => ({
  Terminal: class {
    loadAddon() {}
    open() {}
    write() {}
    reset() {}
    onData(callback: (data: string) => void) {
      onDataMock(callback)
    }
    dispose() {}
  },
}))
vi.mock('@xterm/addon-fit', () => ({
  FitAddon: class {
    fit() {
      fitMock()
    }
  },
}))

describe('useCodeTerminal', () => {
  beforeEach(() => {
    fitMock.mockClear()
    onDataMock.mockClear()
  })
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('subscribes to status and transcript, then unsubscribes', () => {
    let listener: ((event: CodePracticeEvent) => void) | undefined
    const unsubscribe = vi.fn()
    const runner: CodePracticeRunner = {
      start: vi.fn(),
      updateFile: vi.fn(),
      sendStdin: vi.fn(),
      subscribe: vi.fn((callback) => {
        listener = callback
        return unsubscribe
      }),
      dispose: vi.fn(),
    }
    const { result, unmount } = renderHook(() => useCodeTerminal({ runner }))
    act(() => listener?.({ status: 'running', text: '2\n', runId: 1 }))
    expect(result.current.statusText).toBe('Prática em andamento')
    expect(result.current.transcript).toContain('2')
    act(() => listener?.({ status: 'waiting-input', text: '', runId: 1 }))
    expect(result.current.statusText).toBe('')
    unmount()
    expect(unsubscribe).toHaveBeenCalledOnce()
  })

  it('replaces stale output when a new run starts', () => {
    let listener: ((event: CodePracticeEvent) => void) | undefined
    const runner: CodePracticeRunner = {
      start: vi.fn(),
      updateFile: vi.fn(),
      sendStdin: vi.fn(),
      dispose: vi.fn(),
      subscribe: vi.fn((callback) => {
        listener = callback
        return vi.fn()
      }),
    }
    const { result, unmount } = renderHook(() => useCodeTerminal({ runner }))
    act(() => listener?.({ status: 'ready', text: 'old output', runId: 1 }))
    act(() => listener?.({ status: 'running', text: 'new output', runId: 2 }))
    expect(result.current.transcript).toBe('new output')
    unmount()
  })

  it('coalesces resize fitting and ignores unchanged dimensions', async () => {
    let resizeCallback: ResizeObserverCallback | undefined
    const disconnectMock = vi.fn()
    const observeMock = vi.fn()
    vi.stubGlobal(
      'ResizeObserver',
      class {
        constructor(callback: ResizeObserverCallback) {
          resizeCallback = callback
        }

        observe = observeMock
        disconnect = disconnectMock
      },
    )
    const frames: FrameRequestCallback[] = []
    vi.spyOn(window, 'requestAnimationFrame').mockImplementation((callback) => {
      frames.push(callback)
      return frames.length
    })
    const cancelAnimationFrameMock = vi
      .spyOn(window, 'cancelAnimationFrame')
      .mockImplementation(() => {})
    const runner: CodePracticeRunner = {
      start: vi.fn(),
      updateFile: vi.fn(),
      sendStdin: vi.fn(),
      subscribe: vi.fn(() => vi.fn()),
      dispose: vi.fn(),
    }
    const { result, unmount } = renderHook(() => useCodeTerminal({ runner }))
    result.current.terminalElementRef.current = document.createElement('div')
    await waitFor(() => expect(observeMock).toHaveBeenCalledOnce())
    expect(fitMock).toHaveBeenCalledOnce()
    const handleTerminalData = onDataMock.mock.calls[0]?.[0] as
      | ((data: string) => void)
      | undefined
    act(() => {
      handleTerminalData?.('4')
      handleTerminalData?.('\r')
    })
    expect(runner.sendStdin).toHaveBeenCalledWith('4')

    const observeSize = (width: number, height: number) => {
      const entry = { contentRect: { width, height } } as ResizeObserverEntry
      act(() => resizeCallback?.([entry], {} as ResizeObserver))
    }

    observeSize(640, 320)
    observeSize(650, 320)
    expect(frames).toHaveLength(1)
    act(() => frames[0]?.(0))
    expect(fitMock).toHaveBeenCalledTimes(2)

    observeSize(650, 320)
    expect(frames).toHaveLength(2)
    act(() => frames[1]?.(16))
    expect(fitMock).toHaveBeenCalledTimes(2)

    observeSize(640, 320)
    expect(frames).toHaveLength(3)
    unmount()
    expect(cancelAnimationFrameMock).toHaveBeenCalledWith(3)
    expect(disconnectMock).toHaveBeenCalledOnce()
    act(() => frames[2]?.(32))
    expect(fitMock).toHaveBeenCalledTimes(2)
  })
})
