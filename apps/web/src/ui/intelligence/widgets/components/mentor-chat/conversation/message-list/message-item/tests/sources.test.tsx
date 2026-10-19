import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { MentorAttachment } from '@/core/intelligence/mentor-attachment'
import { Sources, type MentorAttachmentSourceView } from '../sources'

const attachment: MentorAttachment = {
  attachmentId: '01J7T8AC91Z5K8M4JQ8C2D6F0F',
  filename: 'resumo.pdf',
  mediaType: 'application/pdf',
  sizeBytes: 64,
  status: 'ready',
  failureCode: null,
  analyzedPages: [],
  illegiblePages: [],
  uninterpretedPages: [],
}

function sourceView(
  overrides: Partial<MentorAttachmentSourceView> = {},
): MentorAttachmentSourceView {
  return {
    source: {
      attachmentId: attachment.attachmentId,
      chunkId: 'chunk-1',
      pageNumber: null,
      locator: '   ',
    },
    attachment,
    url: null,
    error: null,
    ...overrides,
  }
}

describe('Sources', () => {
  afterEach(cleanup)

  it('omits the source section when there are no citations', () => {
    const { container } = render(<Sources sources={[]} onOpen={vi.fn()} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('labels citations without locations, disables failed source opens, and links ready files', () => {
    const onOpen = vi.fn()
    const { rerender } = render(
      <Sources
        sources={[sourceView({ error: 'Não foi possível abrir o arquivo.' })]}
        onOpen={onOpen}
      />,
    )

    const failedButton = screen.getByRole('button', { name: 'resumo.pdf, trecho citado' })
    expect(failedButton).toBeDisabled()
    expect(screen.getByText('Não foi possível abrir o arquivo.')).toBeVisible()
    fireEvent.click(failedButton)
    expect(onOpen).not.toHaveBeenCalled()

    rerender(
      <Sources
        sources={[
          sourceView({
            source: {
              attachmentId: attachment.attachmentId,
              chunkId: 'chunk-2',
              pageNumber: 4,
              locator: '',
            },
            url: 'blob:source',
          }),
        ]}
        onOpen={onOpen}
      />,
    )

    expect(screen.getByRole('link', { name: 'resumo.pdf, página 4' })).toHaveAttribute(
      'download',
      'resumo.pdf',
    )
    expect(screen.getByRole('link', { name: 'resumo.pdf, página 4' })).toHaveAttribute(
      'href',
      'blob:source',
    )
  })
})
