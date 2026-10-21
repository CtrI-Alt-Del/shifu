import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { MentorAttachment } from '@/core/intelligence/mentor-attachment'
import type { MentorDraftAttachment } from '@/ui/intelligence/contexts/mentor-context/types'
import { AttachmentList } from '../attachment-list'

function draftAttachment(
  localKey: string,
  file: File,
  overrides: Partial<MentorDraftAttachment> = {},
): MentorDraftAttachment {
  return {
    localKey,
    uploadKey: `upload-${localKey}`,
    file,
    previewUrl: null,
    attachment: null,
    error: null,
    ...overrides,
  }
}

function attachment(overrides: Partial<MentorAttachment> = {}): MentorAttachment {
  return {
    attachmentId: '01J7T8AC91Z5K8M4JQ8C2D6F0F',
    filename: 'arquivo.png',
    mediaType: 'image/png',
    sizeBytes: 1_250_000,
    status: 'partial',
    failureCode: null,
    analyzedPages: [1],
    illegiblePages: [2],
    uninterpretedPages: [3],
    ...overrides,
  }
}

describe('AttachmentList', () => {
  afterEach(cleanup)

  it('renders no list for an empty draft', () => {
    const { container } = render(
      <AttachmentList attachments={[]} disabled={false} onRemove={vi.fn()} />,
    )
    expect(container).toBeEmptyDOMElement()
  })

  it('announces attachment states and page coverage with safe metadata fallbacks', () => {
    const partialFile = new File(['x'.repeat(1_000_001)], 'parcial.png', {
      type: 'image/png',
    })
    const waitingFile = new File(['texto'], 'aguardando.png', { type: 'image/png' })
    const genericFile = new File([], 'sem-tipo.bin', { type: '' })
    const errorFile = new File(['erro'], 'erro.txt', { type: 'text/plain' })
    const drafts = [
      draftAttachment('partial', partialFile, {
        previewUrl: 'blob:partial',
        attachment: attachment(),
      }),
      draftAttachment('partial-empty', new File(['x'], 'parcial-vazia.pdf'), {
        attachment: attachment({
          attachmentId: 'attachment-empty',
          filename: 'parcial-vazia.pdf',
          mediaType: '',
          analyzedPages: [],
          illegiblePages: [],
          uninterpretedPages: [],
        }),
      }),
      draftAttachment('waiting', waitingFile, { previewUrl: 'blob:waiting' }),
      draftAttachment('generic', genericFile),
      draftAttachment('error', errorFile, {
        error: 'Não foi possível acompanhar o envio.',
      }),
    ]

    render(<AttachmentList attachments={drafts} disabled onRemove={vi.fn()} />)

    expect(screen.getByRole('list', { name: 'Arquivos anexados' })).toBeVisible()
    expect(
      screen.getByText(
        'Páginas analisadas: 1. Páginas ilegíveis: 2. Páginas não analisadas: 3.',
      ),
    ).toBeVisible()
    expect(screen.getByText('Parte do conteúdo não pôde ser interpretada.')).toBeVisible()
    expect(screen.getAllByText('Aguardando envio…')).toHaveLength(2)
    expect(screen.getAllByText('ARQUIVO · 1 KB')).toHaveLength(2)
    expect(screen.getByText('IMAGE/PNG · 1,0 MB')).toBeVisible()
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Não foi possível acompanhar o envio.',
    )
    expect(screen.getByRole('alert')).not.toHaveAttribute('aria-live')
    expect(screen.getAllByRole('status')).toHaveLength(4)
    expect(screen.getByRole('button', { name: 'Remover parcial.png' })).toBeDisabled()
    expect(screen.getByRole('img', { name: 'Prévia de parcial.png' })).toHaveAttribute(
      'src',
      'blob:partial',
    )
  })

  it('restores focus through the remove callback when attachment controls are enabled', () => {
    const onRemove = vi.fn()
    render(
      <AttachmentList
        attachments={[draftAttachment('local-1', new File(['x'], 'resumo.txt'))]}
        disabled={false}
        onRemove={onRemove}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Remover resumo.txt' }))
    expect(onRemove).toHaveBeenCalledWith('local-1')
  })

  it('shows an upload retry action for retryable drafts', () => {
    const onRetry = vi.fn()
    render(
      <AttachmentList
        attachments={[
          draftAttachment('retry', new File(['x'], 'resumo.txt'), {
            error: 'Falha temporária.',
            retryable: true,
          }),
        ]}
        disabled={false}
        onRemove={vi.fn()}
        onRetry={onRetry}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    expect(onRetry).toHaveBeenCalledWith('retry')
  })
})
