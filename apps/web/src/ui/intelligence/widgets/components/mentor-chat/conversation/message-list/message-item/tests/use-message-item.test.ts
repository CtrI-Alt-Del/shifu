import { act, cleanup, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { MentorResponseSnapshot } from '@/core/intelligence/mentor-response'
import type { MentorMessage } from '@/rest/services/intelligence-service'
import { useMentorContext } from '@/ui/intelligence/hooks/use-mentor-context'
import { useMessageItem } from '../use-message-item'
vi.mock('@/ui/intelligence/hooks/use-mentor-context', () => ({
  useMentorContext: vi.fn(),
}))
const shouldAnimateBlock = vi.fn()
const markBlockPresented = vi.fn()
const clipboardWriteTextMock = vi.fn()
const message: MentorMessage = {
  id: 'learner',
  sessionId: 'session',
  role: 'learner',
  content: 'Mensagem do aprendiz',
  createdAt: '2026-10-11T21:19:00-03:00',
  inReplyToMessageId: null,
}
const snapshot: MentorResponseSnapshot = {
  attemptId: 'attempt',
  learnerMessageId: 'learner',
  status: 'processing',
  blocks: [
    {
      blockKey: 'block',
      ordinal: 0,
      intent: null,
      content: 'Texto aprovado completo e acessível',
    },
  ],
  consultations: [],
  lastSequence: 1,
  failureCode: null,
}
describe('useMessageItem', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    clipboardWriteTextMock.mockReset().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', {
      clipboard: { writeText: clipboardWriteTextMock },
    })
    shouldAnimateBlock.mockReturnValue(true)
    markBlockPresented.mockReset()
    vi.mocked(useMentorContext).mockReturnValue({
      shouldAnimateBlock,
      markBlockPresented,
    } as unknown as ReturnType<typeof useMentorContext>)
    vi.stubGlobal(
      'matchMedia',
      vi.fn(() => ({
        matches: false,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      })),
    )
  })
  afterEach(() => {
    cleanup()
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })
  it('types only a new foreground approved block and marks presentation before remount', () => {
    const { result, unmount } = renderHook(() => useMessageItem(message, snapshot))
    expect(result.current.visibleLength['attempt:block']).toBe(0)
    expect(markBlockPresented).toHaveBeenCalledWith('attempt', 'block')
    act(() => vi.advanceTimersByTime(20))
    expect(result.current.visibleLength['attempt:block']).toBe(8)
    act(() => vi.advanceTimersByTime(200))
    expect(result.current.visibleLength['attempt:block']).toBe(
      snapshot.blocks[0]?.content.length,
    )
    unmount()
    expect(vi.getTimerCount()).toBe(0)
  })
  it('continues typing through status, consultation and completion snapshots', () => {
    const { result, rerender, unmount } = renderHook(
      ({ response }) => useMessageItem(message, response),
      { initialProps: { response: snapshot } },
    )
    act(() => vi.advanceTimersByTime(20))
    shouldAnimateBlock.mockReturnValue(false)
    for (const response of [
      { ...snapshot, lastSequence: 2 },
      { ...snapshot, consultations: ['learning' as const], lastSequence: 3 },
      { ...snapshot, status: 'completed' as const, lastSequence: 4 },
    ]) {
      rerender({ response })
      expect(result.current.visibleLength['attempt:block']).toBe(8)
      expect(result.current.blocks[0]?.isTyping).toBe(true)
    }
    act(() => vi.advanceTimersByTime(20))
    expect(result.current.visibleLength['attempt:block']).toBe(16)
    expect(markBlockPresented).toHaveBeenCalledTimes(1)
    unmount()
    expect(vi.getTimerCount()).toBe(0)
  })

  it('starts a later approved block without interrupting the first block', () => {
    const { result, rerender } = renderHook(
      ({ response }) => useMessageItem(message, response),
      { initialProps: { response: snapshot } },
    )
    act(() => vi.advanceTimersByTime(20))
    rerender({
      response: {
        ...snapshot,
        blocks: [
          ...snapshot.blocks,
          {
            blockKey: 'second',
            ordinal: 1,
            intent: null,
            content: 'Outro texto aprovado',
          },
        ],
      },
    })
    expect(result.current.visibleLength['attempt:block']).toBe(8)
    expect(result.current.visibleLength['attempt:second']).toBe(0)
    act(() => vi.advanceTimersByTime(20))
    expect(result.current.visibleLength['attempt:block']).toBe(16)
    expect(result.current.visibleLength['attempt:second']).toBe(8)
  })
  it.each([true, false])(
    'renders complete approved text for reduced motion or replay (%s)',
    (reduced) => {
      vi.stubGlobal(
        'matchMedia',
        vi.fn(() => ({
          matches: reduced,
          addEventListener: vi.fn(),
          removeEventListener: vi.fn(),
        })),
      )
      shouldAnimateBlock.mockReturnValue(reduced)
      const { result } = renderHook(() => useMessageItem(message, snapshot))
      expect(result.current.visibleLength['attempt:block']).toBe(
        snapshot.blocks[0]?.content.length,
      )
      expect(vi.getTimerCount()).toBe(0)
    },
  )

  it('formats the message time, identifies the speaker and derives copy content', () => {
    const initialProps: {
      currentMessage: MentorMessage
      response: MentorResponseSnapshot | null
    } = { currentMessage: message, response: snapshot }
    const { result, rerender } = renderHook(
      ({
        currentMessage,
        response,
      }: {
        currentMessage: MentorMessage
        response: MentorResponseSnapshot | null
      }) => useMessageItem(currentMessage, response),
      { initialProps },
    )

    expect(result.current.timeLabel).toBe('21:19')
    expect(result.current.speakerLabel).toBeNull()
    expect(result.current.copyContent).toBe('Texto aprovado completo e acessível')
    expect(result.current.hasResponse).toBe(true)

    const mentorMessage = { ...message, role: 'mentor' as const }
    rerender({ currentMessage: mentorMessage, response: null })

    expect(result.current.speakerLabel).toBe('Mentor')
    expect(result.current.copyContent).toBe(mentorMessage.content)
    expect(result.current.timeLabel).toBe('21:19')
    expect(result.current.hasResponse).toBe(false)
  })

  it('confirms copied messages and restores the copy state after two seconds', async () => {
    const { result, unmount } = renderHook(() => useMessageItem(message, null))

    expect(result.current.copyLabel).toBe('Copiar')
    expect(result.current.copyAccessibleLabel).toBe('Copiar mensagem')
    expect(result.current.copyIconName).toBe('copy')
    await act(async () => result.current.handleCopyMessage())

    expect(clipboardWriteTextMock).toHaveBeenCalledWith(message.content)
    expect(result.current.isCopied).toBe(true)
    expect(result.current.copyLabel).toBe('Copiada')
    expect(result.current.copyAccessibleLabel).toBe('Mensagem copiada')
    expect(result.current.copyIconName).toBe('circle-check')
    expect(result.current.copyError).toBe(false)

    act(() => vi.advanceTimersByTime(1999))
    expect(result.current.isCopied).toBe(true)

    act(() => vi.advanceTimersByTime(1))
    expect(result.current.isCopied).toBe(false)
    expect(result.current.copyLabel).toBe('Copiar')
    expect(result.current.copyAccessibleLabel).toBe('Copiar mensagem')
    expect(result.current.copyIconName).toBe('copy')

    await act(async () => result.current.handleCopyMessage())
    unmount()
    expect(vi.getTimerCount()).toBe(0)
  })

  it('exposes an accessible error state when copying fails', async () => {
    clipboardWriteTextMock.mockRejectedValueOnce(new Error('Clipboard unavailable'))
    const { result } = renderHook(() => useMessageItem(message, null))

    await act(async () => result.current.handleCopyMessage())

    expect(result.current.isCopied).toBe(false)
    expect(result.current.copyError).toBe(true)
  })
})
