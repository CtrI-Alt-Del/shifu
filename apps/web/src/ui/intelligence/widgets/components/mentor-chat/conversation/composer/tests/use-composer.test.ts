import { act, cleanup, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { MentorContextValue } from '@/ui/intelligence/contexts/mentor-context/types'
import { useMentorContext } from '@/ui/intelligence/hooks/use-mentor-context'
import { useComposer } from '../use-composer'

vi.mock('@/ui/intelligence/hooks/use-mentor-context', () => ({
  useMentorContext: vi.fn(),
}))
const useMentorContextMock = vi.mocked(useMentorContext)

describe('useComposer', () => {
  afterEach(cleanup)

  it('grows, wraps on width changes, and shrinks when the draft clears', () => {
    let notify = () => {}
    const disconnect = vi.fn()
    vi.stubGlobal(
      'ResizeObserver',
      class {
        constructor(callback: () => void) {
          notify = callback
        }
        observe = vi.fn()
        disconnect = disconnect
      },
    )
    const context = { draft: '', selectedSessionId: null }
    useMentorContextMock.mockReturnValue(context as unknown as MentorContextValue)
    const { result, rerender, unmount } = renderHook(() => useComposer())
    const textarea = document.createElement('textarea')
    let height = 84
    let width = 400
    Object.defineProperties(textarea, {
      scrollHeight: { get: () => height },
      clientWidth: { get: () => width },
    })
    result.current.textareaRef.current = textarea
    context.draft = 'three\ntext\nlines'
    rerender()
    expect(textarea.style.height).toBe('84px')
    height = 124
    act(() => notify())
    expect(textarea.style.height).toBe('84px')
    width = 200
    act(() => notify())
    expect(textarea.style.height).toBe('124px')
    height = 44
    context.draft = ''
    rerender()
    expect(textarea.style.height).toBe('44px')
    unmount()
    expect(disconnect).toHaveBeenCalledTimes(2)
    vi.unstubAllGlobals()
  })

  it('resizes drafts without ResizeObserver support', () => {
    vi.stubGlobal('ResizeObserver', undefined)
    const context = { draft: '', selectedSessionId: null }
    useMentorContextMock.mockReturnValue(context as unknown as MentorContextValue)
    const { result, rerender } = renderHook(() => useComposer())
    const textarea = document.createElement('textarea')
    Object.defineProperty(textarea, 'scrollHeight', { value: 64 })
    result.current.textareaRef.current = textarea
    context.draft = 'two\nlines'
    rerender()
    expect(textarea.style.height).toBe('64px')
    vi.unstubAllGlobals()
  })

  it('permits subsequent sends after the response completes', () => {
    useMentorContextMock.mockReturnValue({
      selectedSessionId: 'session-1',
      draft: 'texto',
      isSubmittingFirstMessage: false,
      sendFirstMessage: vi.fn(),
      setDraft: vi.fn(),
      submissionError: null,
    } as unknown as MentorContextValue)
    const { result } = renderHook(() => useComposer())
    expect(result.current.hasAcceptedSession).toBe(true)
    expect(result.current.canSend).toBe(true)
  })

  it('requires non-whitespace text and blocks sending while submission is pending', () => {
    useMentorContextMock.mockReturnValue({
      selectedSessionId: null,
      draft: '   ',
      isSubmittingFirstMessage: false,
      sendFirstMessage: vi.fn(),
      setDraft: vi.fn(),
      submissionError: null,
    } as unknown as MentorContextValue)
    const { result, rerender } = renderHook(() => useComposer())
    expect(result.current.canSend).toBe(false)
    const preventDefault = vi.fn()
    result.current.handleSubmit({
      preventDefault,
    } as unknown as React.FormEvent<HTMLFormElement>)
    expect(preventDefault).toHaveBeenCalledOnce()

    useMentorContextMock.mockReturnValue({
      selectedSessionId: null,
      draft: 'Dúvida',
      isSubmittingFirstMessage: true,
      sendFirstMessage: vi.fn(),
      setDraft: vi.fn(),
      submissionError: null,
    } as unknown as MentorContextValue)
    rerender()
    expect(result.current.canSend).toBe(false)
  })
})

describe('useComposer dictation', () => {
  afterEach(cleanup)
  it.each(['preparing', 'recording', 'transcribing'])(
    'blocks sending and Enter during dictation: %s',
    (dictationStatus) => {
      const sendFirstMessage = vi.fn()
      useMentorContextMock.mockReturnValue({
        draft: 'Texto',
        dictationStatus,
        isDictationBusy: true,
        sendFirstMessage,
      } as unknown as MentorContextValue)
      const { result } = renderHook(() => useComposer())
      const preventDefault = vi.fn()
      const requestSubmit = vi.fn()
      expect(result.current.canSend).toBe(false)
      result.current.handleSubmit({
        preventDefault,
      } as unknown as React.FormEvent<HTMLFormElement>)
      result.current.handleKeyDown({
        key: 'Enter',
        shiftKey: false,
        nativeEvent: { isComposing: false },
        preventDefault,
        currentTarget: { form: { requestSubmit } },
      } as unknown as React.KeyboardEvent<HTMLTextAreaElement>)
      expect(preventDefault).toHaveBeenCalledTimes(2)
      expect(requestSubmit).not.toHaveBeenCalled()
      expect(sendFirstMessage).not.toHaveBeenCalled()
    },
  )
  it('returns focus after the reviewed transcript reaches the editable draft', () => {
    const context = {
      draft: 'Original',
      dictationStatus: 'recording',
      releaseDictationSurface: vi.fn(),
    }
    useMentorContextMock.mockReturnValue(context as unknown as MentorContextValue)
    const { result, rerender, unmount } = renderHook(() => useComposer('page'))
    const textarea = document.createElement('textarea')
    const focus = vi.spyOn(textarea, 'focus')
    result.current.textareaRef.current = textarea
    context.dictationStatus = 'review'
    context.draft = 'Original\nDitado'
    rerender()
    expect(focus).toHaveBeenCalledOnce()
    unmount()
    expect(context.releaseDictationSurface).toHaveBeenCalledWith('page')
  })
})
