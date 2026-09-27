import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { CodePracticeRunner } from '@/core/learning/code-practice-runner'
import { type CodeQuestionProps, useCodeQuestion } from '../use-code-question'

const question: CodeQuestionProps['question'] = {
  key: 'q1',
  prompt: 'Conte vogais',
  initialFiles: [
    { path: 'main.js', content: 'old', editable: true },
    { path: 'locked.js', content: 'fixed', editable: false },
  ],
  entrypoint: 'main.js',
  editablePaths: ['main.js'],
  fixedDependencies: [],
  permittedCommands: [],
}

function runner(): CodePracticeRunner {
  return {
    start: vi.fn().mockResolvedValue(undefined),
    updateFile: vi.fn().mockResolvedValue(undefined),
    sendStdin: vi.fn().mockResolvedValue(undefined),
    subscribe: vi.fn().mockReturnValue(vi.fn()),
    dispose: vi.fn(),
  }
}

describe('useCodeQuestion', () => {
  it('starts practice, edits allowed paths, freezes assessment source and disposes', async () => {
    const practice = runner()
    const onFilesChange = vi.fn()
    const onAssess = vi.fn().mockResolvedValue(undefined)
    const { result, unmount } = renderHook(() =>
      useCodeQuestion({
        question,
        onFilesChange,
        onAssess,
        runnerFactory: () => practice,
      }),
    )
    await waitFor(() => expect(practice.start).toHaveBeenCalledOnce())
    act(() => result.current.handleSelectFile('locked.js'))
    expect(result.current.selectedPath).toBe('locked.js')
    act(() => result.current.handleSelectFile('not-in-project.js'))
    expect(result.current.selectedPath).toBe('locked.js')
    act(() => result.current.handleFileChange('locked.js', 'bad'))
    expect(onFilesChange).not.toHaveBeenCalled()
    act(() => result.current.handleFileChange('main.js', 'new'))
    expect(onFilesChange).toHaveBeenCalledWith([{ path: 'main.js', content: 'new' }])
    await act(() => result.current.handleAssess())
    expect(onAssess).toHaveBeenCalledWith([{ path: 'main.js', content: 'new' }])
    unmount()
    expect(practice.dispose).toHaveBeenCalledOnce()
  })

  it('keeps editing available after assessment failure', async () => {
    const onAssess = vi.fn().mockRejectedValue(new Error('unavailable'))
    const { result } = renderHook(() =>
      useCodeQuestion({ question, onAssess, runnerFactory: runner }),
    )
    await act(() => result.current.handleAssess())
    expect(result.current.hasAssessError).toBe(true)
    expect(result.current.isFrozen).toBe(false)
  })

  it('does not start practice or accept edits in read only mode', () => {
    const runnerFactory = vi.fn(runner)
    const onFilesChange = vi.fn()
    const { result } = renderHook(() =>
      useCodeQuestion({ question, readOnly: true, runnerFactory, onFilesChange }),
    )
    act(() => result.current.handleFileChange('main.js', 'bad'))
    expect(onFilesChange).not.toHaveBeenCalled()
    expect(runnerFactory).not.toHaveBeenCalled()
  })

  it('marks practice unavailable when no runner factory is injected', async () => {
    const { result } = renderHook(() => useCodeQuestion({ question }))
    await waitFor(() => expect(result.current.practiceStatus).toBe('unavailable'))
    expect(result.current.runner).toBeNull()
  })

  it('bounds keyboard and pointer resizing without changing code or practice', () => {
    const practice = runner()
    const { result } = renderHook(() =>
      useCodeQuestion({ question, runnerFactory: () => practice }),
    )
    const workspace = document.createElement('div')
    const sidebar = document.createElement('div')
    workspace.append(sidebar)
    workspace.getBoundingClientRect = vi.fn(() => ({ width: 1200 }) as DOMRect)
    Object.defineProperty(workspace, 'clientWidth', { value: 1198 })
    sidebar.getBoundingClientRect = vi.fn(() => ({ width: 280 }) as DOMRect)
    result.current.workspaceRef.current = workspace
    const editorGrid = document.createElement('div')
    const editor = document.createElement('div')
    editorGrid.append(editor)
    editorGrid.getBoundingClientRect = vi.fn(() => ({ width: 912 }) as DOMRect)
    Object.defineProperty(editorGrid, 'clientWidth', { value: 912 })
    editor.getBoundingClientRect = vi.fn(() => ({ width: 497 }) as DOMRect)
    result.current.editorGridRef.current = editorGrid

    const preventDefault = vi.fn()
    act(() =>
      result.current.handleResizeKeyDown('sidebar', {
        key: 'Home',
        shiftKey: false,
        preventDefault,
      } as never),
    )
    expect(result.current.sidebarWidth).toBe(220)
    act(() =>
      result.current.handleResizeKeyDown('editor', {
        key: 'ArrowRight',
        shiftKey: false,
        preventDefault,
      } as never),
    )
    expect(result.current.editorWidth).toBe(513)

    const target = {
      focus: vi.fn(),
      setPointerCapture: vi.fn(),
      hasPointerCapture: vi.fn(() => true),
      releasePointerCapture: vi.fn(),
    }
    act(() =>
      result.current.handleResizePointerDown('editor', {
        button: 0,
        clientX: 300,
        pointerId: 1,
        currentTarget: target,
        preventDefault,
      } as never),
    )
    act(() =>
      result.current.handleResizePointerMove('editor', {
        clientX: 900,
      } as never),
    )
    expect(result.current.editorWidth).toBe(664)
    act(() =>
      result.current.handleResizeKeyDown('sidebar', {
        key: 'End',
        shiftKey: false,
        preventDefault,
      } as never),
    )
    expect(result.current.sidebarWidth).toBe(662)
    expect(result.current.editorWidth).toBe(280)
    expect(result.current.resizeValues.editor.current).toBe(280)
    expect(
      1198 - result.current.sidebarWidth - 8 - (result.current.editorWidth ?? 0) - 8,
    ).toBe(240)
    act(() =>
      result.current.handleResizePointerEnd({
        pointerId: 1,
        currentTarget: target,
      } as never),
    )
    expect(target.releasePointerCapture).toHaveBeenCalledWith(1)
    expect(result.current.files).toEqual([
      { path: 'main.js', content: 'old' },
      { path: 'locked.js', content: 'fixed' },
    ])
    expect(practice.dispose).not.toHaveBeenCalled()
    expect(preventDefault).toHaveBeenCalled()
  })

  it('clamps a widened editor after the viewport narrows', () => {
    let notifyResize = () => {}
    class ResizeObserverStub {
      constructor(callback: ResizeObserverCallback) {
        notifyResize = () => callback([], this as ResizeObserver)
      }
      observe() {}
      unobserve() {}
      disconnect() {}
    }
    vi.stubGlobal('ResizeObserver', ResizeObserverStub)
    try {
      const { result } = renderHook(() => useCodeQuestion({ question }))
      let workspaceWidth = 1400
      let editorGridWidth = 1112
      const workspace = document.createElement('div')
      workspace.getBoundingClientRect = vi.fn(
        () => ({ width: workspaceWidth }) as DOMRect,
      )
      Object.defineProperty(workspace, 'clientWidth', {
        get: () => workspaceWidth - 2,
      })
      const editorGrid = document.createElement('div')
      editorGrid.getBoundingClientRect = vi.fn(
        () => ({ width: editorGridWidth }) as DOMRect,
      )
      Object.defineProperty(editorGrid, 'clientWidth', {
        get: () => editorGridWidth,
      })
      result.current.workspaceRef.current = workspace
      result.current.editorGridRef.current = editorGrid
      act(notifyResize)
      act(() =>
        result.current.handleResizeKeyDown('editor', {
          key: 'End',
          shiftKey: false,
          preventDefault: vi.fn(),
        } as never),
      )
      expect(result.current.editorWidth).toBe(864)

      workspaceWidth = 1200
      editorGridWidth = 912
      act(notifyResize)
      expect(result.current.editorWidth).toBe(664)
      expect(result.current.resizeValues.editor.current).toBe(664)
      expect(result.current.resizeValues.editor.maximum).toBe(664)
    } finally {
      vi.unstubAllGlobals()
    }
  })
})
