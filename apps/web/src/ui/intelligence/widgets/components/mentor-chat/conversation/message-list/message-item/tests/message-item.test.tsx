import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { MentorAttachment } from '@/core/intelligence/mentor-attachment'
import { MessageItem } from '..'
import { useMessageItem } from '../use-message-item'

vi.mock('../use-message-item', () => ({ useMessageItem: vi.fn() }))
const useMessageItemMock = vi.mocked(useMessageItem)
const handleOpenAttachment = vi.fn()
const handleCopyMessage = vi.fn()
const attachment: MentorAttachment = {
  attachmentId: '01J7T8AC91Z5K8M4JQ8C2D6F0B',
  filename: 'desenho.png',
  mediaType: 'image/png',
  sizeBytes: 6_000,
  status: 'partial',
  failureCode: null,
  analyzedPages: [1, 2],
  illegiblePages: [3],
  uninterpretedPages: [],
}
const makeHookValue = (
  overrides: Partial<ReturnType<typeof useMessageItem>> = {},
): ReturnType<typeof useMessageItem> => ({
  blocks: [],
  attachments: [],
  visibleLength: {},
  handleOpenAttachment,
  shouldAnimateEntrance: false,
  shouldReduceMotion: true,
  copyAccessibleLabel: 'Copiar mensagem',
  copyContent: 'Resposta do Mentor',
  copyError: false,
  copyIconName: 'copy',
  copyLabel: 'Copiar',
  hasResponse: false,
  isCopied: false,
  isLearnerMessage: false,
  isMentorMessage: true,
  speakerLabel: 'Mentor',
  timeLabel: null,
  handleCopyMessage,
  ...overrides,
})

describe('MessageItem', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useMessageItemMock.mockReturnValue(makeHookValue())
  })
  afterEach(cleanup)

  it('renders historical image previews with filename and partial page coverage', () => {
    useMessageItemMock.mockReturnValue(
      makeHookValue({
        isLearnerMessage: true,
        isMentorMessage: false,
        speakerLabel: null,
        attachments: [{ attachment, url: 'blob:private-preview', error: null }],
      }),
    )
    render(
      <ol>
        <MessageItem
          message={{
            id: 'learner',
            sessionId: 'session',
            role: 'learner',
            content: 'Veja a imagem.',
            createdAt: '2026-10-14T12:00:00Z',
            inReplyToMessageId: null,
            attachments: [attachment],
          }}
        />
      </ol>,
    )
    expect(screen.getByRole('img', { name: 'Prévia de desenho.png' })).toHaveAttribute(
      'src',
      'blob:private-preview',
    )
    expect(screen.getByText('desenho.png')).toBeVisible()
    expect(screen.getByText(/Páginas analisadas: 1, 2/)).toBeVisible()
    expect(screen.getByText(/Páginas ilegíveis: 3/)).toBeVisible()
  })

  it('shows only supplied source rows and delegates opening to the owning hook', () => {
    const source = {
      attachmentId: attachment.attachmentId,
      chunkId: 'chunk-1',
      pageNumber: 2,
      locator: 'Exemplo resolvido',
    }
    useMessageItemMock.mockReturnValue(
      makeHookValue({
        hasResponse: true,
        blocks: [
          {
            blockKey: 'answer',
            ordinal: 0,
            intent: null,
            content: 'Resposta citada.',
            displayedContent: 'Resposta citada.',
            isTyping: false,
            sources: [{ source, attachment, url: null, error: null }],
          },
        ],
      }),
    )
    const { rerender } = render(
      <ol>
        <MessageItem
          message={{
            id: 'mentor',
            sessionId: 'session',
            role: 'mentor',
            content: '',
            createdAt: '',
            inReplyToMessageId: 'learner',
            attachments: [],
          }}
        />
      </ol>,
    )
    const sourceButton = screen.getByRole('button', {
      name: 'desenho.png, página 2, Exemplo resolvido',
    })
    fireEvent.click(sourceButton)
    expect(handleOpenAttachment).toHaveBeenCalledWith(attachment.attachmentId)

    useMessageItemMock.mockReturnValue(
      makeHookValue({
        hasResponse: true,
        blocks: [
          {
            blockKey: 'answer',
            ordinal: 0,
            intent: null,
            content: 'Resposta citada.',
            displayedContent: 'Resposta citada.',
            isTyping: false,
            sources: [{ source, attachment, url: 'blob:source', error: null }],
          },
        ],
      }),
    )
    rerender(
      <ol>
        <MessageItem
          message={{
            id: 'mentor',
            sessionId: 'session',
            role: 'mentor',
            content: '',
            createdAt: '',
            inReplyToMessageId: 'learner',
            attachments: [],
          }}
        />
      </ol>,
    )
    expect(
      screen.getByRole('link', { name: 'desenho.png, página 2, Exemplo resolvido' }),
    ).toHaveAttribute('href', 'blob:source')
    expect(
      screen.getByRole('link', { name: 'desenho.png, página 2, Exemplo resolvido' }),
    ).toHaveAttribute('download', 'desenho.png')
  })

  it('renders historical status, processing, and error states without exposing missing previews', () => {
    const readyPdf = {
      ...attachment,
      attachmentId: 'ready-pdf',
      filename: 'pronto.pdf',
      mediaType: 'application/pdf',
      status: 'ready' as const,
      analyzedPages: [],
      illegiblePages: [],
      uninterpretedPages: [],
    }
    const failedImage = {
      ...attachment,
      attachmentId: 'failed-image',
      filename: 'falhou.png',
      status: 'failed' as const,
    }
    const processingImage = {
      ...attachment,
      attachmentId: 'processing-image',
      filename: 'processando.jpg',
      mediaType: 'image/jpeg',
      status: 'processing' as const,
      analyzedPages: [],
      illegiblePages: [],
      uninterpretedPages: [],
    }
    const partialText = {
      ...attachment,
      attachmentId: 'partial-text',
      filename: 'parcial.txt',
      mediaType: 'text/plain',
      analyzedPages: [],
      illegiblePages: [],
      uninterpretedPages: [],
    }
    useMessageItemMock.mockReturnValue(
      makeHookValue({
        attachments: [
          { attachment: readyPdf, url: null, error: null },
          { attachment: failedImage, url: null, error: 'Arquivo bloqueado.' },
          { attachment: processingImage, url: null, error: null },
          { attachment: partialText, url: null, error: null },
        ],
        copyContent: '',
        timeLabel: '09:30',
        isLearnerMessage: true,
        isMentorMessage: false,
        speakerLabel: null,
        shouldAnimateEntrance: true,
        shouldReduceMotion: false,
      }),
    )

    render(
      <ol>
        <MessageItem
          message={{
            id: 'learner',
            sessionId: 'session',
            role: 'learner',
            content: 'Arquivos da conversa.',
            createdAt: '2026-10-14T12:00:00Z',
            inReplyToMessageId: null,
            attachments: [readyPdf, failedImage, processingImage, partialText],
          }}
          surface='fab'
        />
      </ol>,
    )

    expect(screen.getByText(/Arquivo disponível/)).toBeVisible()
    expect(screen.getByText(/Arquivo não interpretado/)).toBeVisible()
    expect(screen.getByText(/Arquivo indisponível/)).toBeVisible()
    expect(screen.getByText('Parte do conteúdo não pôde ser interpretada.')).toBeVisible()
    expect(screen.getByText('Carregando prévia do arquivo…')).toBeVisible()
    expect(screen.getByText('Arquivo bloqueado.')).toBeVisible()
    expect(screen.getByText('09:30')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Copiar mensagem' })).toBeDisabled()
    expect(screen.getByText('Arquivos da conversa.')).toBeVisible()
    expect(
      screen.queryByRole('img', { name: 'Prévia de falhou.png' }),
    ).not.toBeInTheDocument()
  })
})
