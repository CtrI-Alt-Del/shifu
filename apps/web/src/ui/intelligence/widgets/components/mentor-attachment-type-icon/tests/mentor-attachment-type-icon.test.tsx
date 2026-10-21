import { cleanup, render } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { MentorAttachmentTypeIcon } from '../index'

describe('MentorAttachmentTypeIcon', () => {
  afterEach(cleanup)

  it.each([
    ['application/pdf', 'lucide-file-type'],
    ['text/plain', 'lucide-file-text'],
    ['application/json', 'lucide-file-json'],
    ['text/csv', 'lucide-file-spreadsheet'],
    ['application/octet-stream', 'lucide-file'],
  ])('maps %s to its file icon', (mediaType, iconClass) => {
    const { container } = render(<MentorAttachmentTypeIcon mediaType={mediaType} />)

    expect(container.querySelector('svg')).toHaveClass(iconClass)
  })
})
