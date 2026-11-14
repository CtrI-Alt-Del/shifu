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

  it.each(['page', 'fab'] as const)(
    'allows prepared attachment-only submissions on %s and blocks incomplete drafts',
    (surface) => {
      const sendFirstMessage = vi.fn()
      const context = {
        draft: '',
        draftAttachments: [{ attachment: { status: 'ready' }, error: null }],
        sendFirstMessage,
      }
      useMentorContextMock.mockReturnValue(context as unknown as MentorContextValue)
      const { result, rerender } = renderHook(() => useComposer(surface))
      expect(result.current.canSend).toBe(true)
      result.current.handleSubmit({
        preventDefault: vi.fn(),
      } as unknown as React.FormEvent<HTMLFormElement>)
      expect(sendFirstMessage).toHaveBeenCalledWith(surface)
      context.draft = '   '
      context.draftAttachments[0].attachment.status = 'partial'
      rerender()
      expect(result.current.canSend).toBe(true)
      for (const status of ['uploading', 'processing', 'failed', 'removed']) {
        context.draftAttachments[0].attachment.status = status
        rerender()
        expect(result.current.canSend).toBe(false)
      }
      context.draftAttachments = []
      rerender()
      expect(result.current.canSend).toBe(false)
    },
  )

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

  it('switches the placeholder and blocks sending while the context is being summarized', () => {
    const context = {
      selectedSessionId: 'session-1',
      draft: 'texto',
      isSubmittingFirstMessage: false,
      isSummarizingContext: false,
      sessionDetail: { pendingLearnerMessageId: null as string | null },
      sendFirstMessage: vi.fn(),
      setDraft: vi.fn(),
      submissionError: null,
    }
    useMentorContextMock.mockReturnValue(context as unknown as MentorContextValue)
    const { result, rerender } = renderHook(() => useComposer())
    expect(result.current.placeholder).toBe('Pergunte ao Mentor…')
    expect(result.current.canSend).toBe(true)

    context.isSummarizingContext = true
    context.sessionDetail = { pendingLearnerMessageId: 'learner' }
    rerender()
    expect(result.current.placeholder).toBe('Aguarde enquanto o contexto é resumido')
    expect(result.current.isResponsePending).toBe(true)
    expect(result.current.canSend).toBe(false)
    expect(result.current.canManageAttachments).toBe(false)
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

describe('useComposer action block', () => {
  afterEach(cleanup)

  function blockedContext(overrides: object = {}) {
    return {
      selectedSessionId: 'session-1',
      draft: 'texto',
      draftAttachments: [{ attachment: { status: 'ready' }, error: null }],
      isSubmittingFirstMessage: false,
      isDictationBusy: false,
      canStartDictation: true,
      sessionDetail: { pendingLearnerMessageId: null },
      blockingActionProposalId: 'proposal-1',
      isRefreshingActions: false,
      hasActionRefreshTimedOut: false,
      refreshActions: vi.fn(),
      sendFirstMessage: vi.fn(),
      setDraft: vi.fn(),
      ...overrides,
    }
  }

  it('blocks sending, attachments and dictation while a proposal needs an answer', () => {
    const context = blockedContext()
    useMentorContextMock.mockReturnValue(context as unknown as MentorContextValue)
    const { result } = renderHook(() => useComposer())

    expect(result.current.isActionBlocked).toBe(true)
    expect(result.current.canSend).toBe(false)
    expect(result.current.canManageAttachments).toBe(false)
    expect(result.current.canStartDictation).toBe(false)
    result.current.handleSubmit({
      preventDefault: vi.fn(),
    } as unknown as React.FormEvent<HTMLFormElement>)
    expect(context.sendFirstMessage).not.toHaveBeenCalled()
  })

  it('ignores the Enter key while a proposal is unresolved', () => {
    useMentorContextMock.mockReturnValue(
      blockedContext() as unknown as MentorContextValue,
    )
    const { result } = renderHook(() => useComposer())
    const requestSubmit = vi.fn()

    result.current.handleKeyDown({
      key: 'Enter',
      shiftKey: false,
      nativeEvent: { isComposing: false },
      preventDefault: vi.fn(),
      currentTarget: { form: { requestSubmit } },
    } as unknown as React.KeyboardEvent<HTMLTextAreaElement>)

    expect(requestSubmit).not.toHaveBeenCalled()
  })

  it('unblocks sending, attachments and dictation once the proposal is final', () => {
    const context = blockedContext()
    useMentorContextMock.mockReturnValue(context as unknown as MentorContextValue)
    const { result, rerender } = renderHook(() => useComposer())

    context.blockingActionProposalId = null as unknown as string
    rerender()

    expect(result.current.isActionBlocked).toBe(false)
    expect(result.current.canSend).toBe(true)
    expect(result.current.canManageAttachments).toBe(true)
    expect(result.current.canStartDictation).toBe(true)
  })

  it('keeps dictation unavailable when the context already forbids it', () => {
    useMentorContextMock.mockReturnValue(
      blockedContext({
        blockingActionProposalId: null,
        canStartDictation: false,
      }) as unknown as MentorContextValue,
    )
    const { result } = renderHook(() => useComposer())

    expect(result.current.canStartDictation).toBe(false)
  })

  it('exposes the refresh state and the retry callback of the context', () => {
    const context = blockedContext({
      isRefreshingActions: true,
      hasActionRefreshTimedOut: true,
    })
    useMentorContextMock.mockReturnValue(context as unknown as MentorContextValue)
    const { result } = renderHook(() => useComposer())

    expect(result.current.isRefreshingActions).toBe(true)
    expect(result.current.hasActionRefreshTimedOut).toBe(true)
    result.current.refreshActions()
    expect(context.refreshActions).toHaveBeenCalledOnce()
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
