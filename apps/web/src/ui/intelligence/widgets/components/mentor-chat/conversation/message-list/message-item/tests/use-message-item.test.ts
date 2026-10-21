import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement, type PropsWithChildren } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AppError } from '@/core/errors/app-error'
import type { MentorResponseSnapshot } from '@/core/intelligence/mentor-response'
import type { MentorMessage } from '@/rest/services/intelligence-service'
import { useMentorContext } from '@/ui/intelligence/hooks/use-mentor-context'
import { useMentorAttachmentFileQuery } from '@/ui/intelligence/hooks/use-mentor-attachment-file-query'
import { useMessageItem } from '../use-message-item'
vi.mock('@/ui/intelligence/hooks/use-mentor-context', () => ({
  useMentorContext: vi.fn(),
}))
vi.mock('@/ui/intelligence/hooks/use-mentor-attachment-file-query', () => ({
  useMentorAttachmentFileQuery: vi.fn(() => ({
    mentorAttachmentFiles: {},
    mentorAttachmentFileErrors: {},
  })),
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
  attachments: [],
}
const imageAttachment = {
  attachmentId: '01J7T8AC91Z5K8M4JQ8C2D6F0F',
  filename: 'foto.png',
  mediaType: 'image/png',
  sizeBytes: 5,
  status: 'ready' as const,
  failureCode: null,
  analyzedPages: [],
  illegiblePages: [],
  uninterpretedPages: [],
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
      sources: [],
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
      selectedSessionId: 'session',
      sessionDetail: {
        messages: { items: [message], nextCursor: null },
      },
    } as unknown as ReturnType<typeof useMentorContext>)
    vi.mocked(useMentorAttachmentFileQuery).mockReturnValue({
      mentorAttachmentFiles: {},
      mentorAttachmentFileErrors: {},
      mentorAttachmentFilesError: null,
      isReadingMentorAttachmentFiles: false,
    })
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
            sources: [],
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

  it('loads an attached image through the MessageItem consumer query', async () => {
    vi.useRealTimers()
    const messageWithImage = { ...message, attachments: [imageAttachment] }
    vi.mocked(useMentorContext).mockReturnValue({
      shouldAnimateBlock,
      markBlockPresented,
      selectedSessionId: 'session',
      sessionDetail: { messages: { items: [messageWithImage], nextCursor: null } },
    } as unknown as ReturnType<typeof useMentorContext>)
    const actualFileQuery = await vi.importActual<
      typeof import('@/ui/intelligence/hooks/use-mentor-attachment-file-query')
    >('@/ui/intelligence/hooks/use-mentor-attachment-file-query')
    let fileQueryData:
      | ReturnType<typeof actualFileQuery.useMentorAttachmentFileQuery>
      | undefined
    vi.mocked(useMentorAttachmentFileQuery).mockImplementation((input) => {
      fileQueryData = actualFileQuery.useMentorAttachmentFileQuery(input)
      return fileQueryData
    })
    const createObjectURL = vi.fn(() => 'blob:mentor-image')
    const revokeObjectURL = vi.fn()
    vi.stubGlobal('URL', Object.assign(URL, { createObjectURL, revokeObjectURL }))
    const fetchMock = vi.fn(
      async () =>
        ({
          ok: true,
          blob: async () => new Blob(['image']),
        }) as Response,
    )
    vi.stubGlobal('fetch', fetchMock)
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const wrapper = ({ children }: PropsWithChildren) =>
      createElement(QueryClientProvider, { client }, children)

    const { result, unmount } = renderHook(() => useMessageItem(messageWithImage, null), {
      wrapper,
    })

    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    await waitFor(() =>
      expect(
        fileQueryData?.mentorAttachmentFiles[imageAttachment.attachmentId],
      ).toBeDefined(),
    )
    await waitFor(() => expect(createObjectURL).toHaveBeenCalled())
    await waitFor(() =>
      expect(result.current.attachments[0]?.url).toBe('blob:mentor-image'),
    )
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/intelligence/mentor-sessions/session/attachments/01J7T8AC91Z5K8M4JQ8C2D6F0F/file?preview=true',
      expect.objectContaining({ credentials: 'same-origin' }),
    )
    expect(result.current.attachments[0]?.error).toBeNull()
    unmount()
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:mentor-image')
    client.clear()
  })

  it('shows not-ready, malformed-response and network errors for attached images', async () => {
    vi.useRealTimers()
    const notReadyId = '01J7T8AC91Z5K8M4JQ8C2D6F0A'
    const networkErrorId = '01J7T8AC91Z5K8M4JQ8C2D6F0C'
    const malformedResponseId = '01J7T8AC91Z5K8M4JQ8C2D6F0D'
    const attachments = [
      { ...imageAttachment, attachmentId: notReadyId },
      { ...imageAttachment, attachmentId: networkErrorId },
      { ...imageAttachment, attachmentId: malformedResponseId },
    ]
    const messageWithImages = { ...message, attachments }
    vi.mocked(useMentorContext).mockReturnValue({
      shouldAnimateBlock,
      markBlockPresented,
      selectedSessionId: 'session',
      sessionDetail: { messages: { items: [messageWithImages], nextCursor: null } },
    } as unknown as ReturnType<typeof useMentorContext>)
    const actualFileQuery = await vi.importActual<
      typeof import('@/ui/intelligence/hooks/use-mentor-attachment-file-query')
    >('@/ui/intelligence/hooks/use-mentor-attachment-file-query')
    vi.mocked(useMentorAttachmentFileQuery).mockImplementation(
      actualFileQuery.useMentorAttachmentFileQuery,
    )
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input)
      if (path.includes(notReadyId))
        return {
          ok: false,
          json: async () => ({ code: 'attachment_not_ready' }),
        } as Response
      if (path.includes(networkErrorId)) throw new Error('network')
      return {
        ok: false,
        json: async () => {
          throw new Error('malformed response')
        },
      } as unknown as Response
    })
    vi.stubGlobal('fetch', fetchMock)
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const wrapper = ({ children }: PropsWithChildren) =>
      createElement(QueryClientProvider, { client }, children)
    const { result, unmount } = renderHook(
      () => useMessageItem(messageWithImages, null),
      { wrapper },
    )

    await waitFor(() =>
      expect(result.current.attachments.map(({ error }) => error)).toEqual([
        'O arquivo ainda está sendo preparado.',
        'Não foi possível abrir este arquivo. Tente novamente.',
        'Não foi possível abrir este arquivo. Tente novamente.',
      ]),
    )
    expect(fetchMock).toHaveBeenCalledTimes(3)
    unmount()
    client.clear()
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

  it('only exposes sources from the response learner message in the selected session', () => {
    const attachment = {
      attachmentId: 'attachment-owned',
      filename: 'exercicio.pdf',
      mediaType: 'application/pdf',
      sizeBytes: 123,
      status: 'ready' as const,
      failureCode: null,
      analyzedPages: [],
      illegiblePages: [],
      uninterpretedPages: [],
    }
    const ownLearnerMessage = {
      ...message,
      id: 'learner',
      attachments: [attachment],
    }
    vi.mocked(useMentorContext).mockReturnValue({
      shouldAnimateBlock,
      markBlockPresented,
      selectedSessionId: 'session',
      sessionDetail: {
        messages: { items: [ownLearnerMessage], nextCursor: null },
      },
    } as unknown as ReturnType<typeof useMentorContext>)
    const originalBlock = snapshot.blocks[0]
    if (!originalBlock) throw new Error('Expected a response block fixture.')
    const response: MentorResponseSnapshot = {
      ...snapshot,
      blocks: [
        {
          ...originalBlock,
          sources: [
            {
              attachmentId: attachment.attachmentId,
              chunkId: 'chunk-1',
              pageNumber: 2,
              locator: 'Exemplo resolvido',
            },
            {
              attachmentId: 'foreign-attachment',
              chunkId: 'chunk-2',
              pageNumber: 99,
              locator: 'Outra conversa',
            },
          ],
        },
      ],
    }
    const { result } = renderHook(() =>
      useMessageItem(
        {
          ...message,
          id: 'mentor-answer',
          role: 'mentor',
          inReplyToMessageId: 'learner',
          attachments: [],
        },
        response,
      ),
    )
    expect(result.current.blocks[0]?.sources).toEqual([
      expect.objectContaining({
        source: expect.objectContaining({ attachmentId: attachment.attachmentId }),
        attachment,
      }),
    ])
    act(() => result.current.handleOpenAttachment(attachment.attachmentId))
    expect(useMentorAttachmentFileQuery).toHaveBeenLastCalledWith(
      expect.objectContaining({
        sessionId: 'session',
        attachmentIds: [attachment.attachmentId],
      }),
    )
  })

  it('loads only ready image previews and authorized requested sources', () => {
    const image = {
      attachmentId: 'image-ready',
      filename: 'quadro.png',
      mediaType: 'image/png',
      sizeBytes: 40,
      status: 'ready' as const,
      failureCode: null,
      analyzedPages: [],
      illegiblePages: [],
      uninterpretedPages: [],
    }
    const failedImage = {
      ...image,
      attachmentId: 'image-failed',
      status: 'failed' as const,
    }
    const pdf = {
      ...image,
      attachmentId: 'pdf-ready',
      filename: 'exercicio.pdf',
      mediaType: 'application/pdf',
    }
    const learner = { ...message, attachments: [image, failedImage, pdf] }
    const response: MentorResponseSnapshot = {
      ...snapshot,
      blocks: [
        {
          blockKey: 'block',
          ordinal: 0,
          intent: null,
          content: 'Resposta.',
          sources: [image, failedImage, pdf].map((item) => ({
            attachmentId: item.attachmentId,
            chunkId: `chunk-${item.attachmentId}`,
            pageNumber: null,
            locator: 'trecho',
          })),
        },
      ],
    }
    vi.mocked(useMentorContext).mockReturnValue({
      shouldAnimateBlock,
      markBlockPresented,
      selectedSessionId: 'session',
      sessionDetail: { messages: { items: [learner], nextCursor: null } },
    } as unknown as ReturnType<typeof useMentorContext>)
    const createObjectURL = vi.fn(() => 'blob:quadro')
    const revokeObjectURL = vi.fn()
    vi.stubGlobal('URL', { createObjectURL, revokeObjectURL })
    vi.mocked(useMentorAttachmentFileQuery).mockReturnValue({
      mentorAttachmentFiles: { [image.attachmentId]: new Blob(['image']) },
      mentorAttachmentFileErrors: {
        [pdf.attachmentId]: new AppError('Prévia indisponível', 'Erro ao abrir arquivo'),
      },
      mentorAttachmentFilesError: null,
      isReadingMentorAttachmentFiles: false,
    })
    const messageWithAttachments = {
      ...message,
      role: 'mentor' as const,
      attachments: [image, failedImage, pdf],
    }

    const { result, rerender, unmount } = renderHook(
      ({ currentMessage, currentResponse }) =>
        useMessageItem(currentMessage, currentResponse),
      {
        initialProps: {
          currentMessage: messageWithAttachments,
          currentResponse: response,
        },
      },
    )

    expect(useMentorAttachmentFileQuery).toHaveBeenLastCalledWith({
      sessionId: 'session',
      attachmentIds: [image.attachmentId],
      previewAttachmentIds: [image.attachmentId],
    })
    expect(result.current.blocks[0]?.sources).toEqual([
      expect.objectContaining({
        source: expect.objectContaining({ attachmentId: image.attachmentId }),
        url: 'blob:quadro',
        error: null,
      }),
      expect.objectContaining({
        source: expect.objectContaining({ attachmentId: pdf.attachmentId }),
        url: null,
        error: 'Prévia indisponível',
      }),
    ])

    act(() => result.current.handleOpenAttachment(pdf.attachmentId))
    rerender({
      currentMessage: messageWithAttachments,
      currentResponse: response,
    })
    expect(useMentorAttachmentFileQuery).toHaveBeenLastCalledWith({
      sessionId: 'session',
      attachmentIds: [image.attachmentId, pdf.attachmentId],
      previewAttachmentIds: [image.attachmentId],
    })
    act(() => result.current.handleOpenAttachment(image.attachmentId))
    rerender({ currentMessage: messageWithAttachments, currentResponse: response })
    expect(useMentorAttachmentFileQuery).toHaveBeenLastCalledWith({
      sessionId: 'session',
      attachmentIds: [image.attachmentId, image.attachmentId],
      previewAttachmentIds: [image.attachmentId, image.attachmentId],
    })
    expect(createObjectURL).toHaveBeenCalledWith(expect.any(Blob))
    unmount()
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:quadro')
  })

  it('clears a typing timer when an approved block changes and excludes a previous session', () => {
    const firstBlock = snapshot.blocks[0]
    if (!firstBlock) throw new Error('Expected a response block fixture.')
    const { rerender, unmount } = renderHook(
      ({ currentMessage, response }) => useMessageItem(currentMessage, response),
      { initialProps: { currentMessage: message, response: snapshot } },
    )
    expect(vi.getTimerCount()).toBe(1)
    rerender({
      currentMessage: message,
      response: {
        ...snapshot,
        blocks: [{ ...firstBlock, content: 'Texto atualizado' }],
      },
    })
    expect(vi.getTimerCount()).toBe(1)
    unmount()
    expect(vi.getTimerCount()).toBe(0)

    vi.mocked(useMentorContext).mockReturnValue({
      shouldAnimateBlock,
      markBlockPresented,
      selectedSessionId: 'another-session',
      sessionDetail: { messages: { items: [message], nextCursor: null } },
    } as unknown as ReturnType<typeof useMentorContext>)
    renderHook(() => useMessageItem(message, snapshot))
    expect(useMentorAttachmentFileQuery).toHaveBeenLastCalledWith({
      sessionId: null,
      attachmentIds: [],
      previewAttachmentIds: [],
    })
  })
})
