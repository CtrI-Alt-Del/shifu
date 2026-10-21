import type {
  MentorAttachment,
  MentorAttachmentSource,
} from '@/core/intelligence/mentor-attachment'

export type MentorAttachmentSourceView = {
  source: MentorAttachmentSource
  attachment: MentorAttachment
  url: string | null
  error: string | null
}

type SourcesProps = {
  sources: MentorAttachmentSourceView[]
  onOpen(attachmentId: string): void
}

function sourceLabel(source: MentorAttachmentSource, attachment: MentorAttachment) {
  const page = source.pageNumber ? `página ${source.pageNumber}` : ''
  const locator = source.locator.trim()
  const location = [page, locator].filter(Boolean).join(', ') || 'trecho citado'
  return `${attachment.filename}, ${location}`
}

export const Sources = ({ sources, onOpen }: SourcesProps) => {
  if (sources.length === 0) return null

  return (
    <section
      aria-label='Fontes consultadas'
      className='mt-3 space-y-1 border-t border-border pt-2'
    >
      <p className='text-xs font-semibold text-muted-foreground'>Fontes</p>
      <ul className='space-y-1'>
        {sources.map(({ source, url, error, ...item }) => (
          <li className='text-xs' key={`${source.attachmentId}:${source.chunkId}`}>
            {url ? (
              <a
                className='min-h-11 inline-flex items-center underline underline-offset-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-selo-text'
                download={item.attachment.filename}
                href={url}
              >
                {sourceLabel(source, item.attachment)}
              </a>
            ) : (
              <button
                className='min-h-11 max-w-full text-left underline underline-offset-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-selo-text disabled:opacity-50'
                disabled={Boolean(error)}
                onClick={() => onOpen(source.attachmentId)}
                type='button'
              >
                {sourceLabel(source, item.attachment)}
              </button>
            )}
            {error ? <output className='block'>{error}</output> : null}
          </li>
        ))}
      </ul>
    </section>
  )
}
