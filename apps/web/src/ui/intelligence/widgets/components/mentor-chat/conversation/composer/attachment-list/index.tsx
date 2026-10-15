import type { MentorDraftAttachment } from '@/ui/intelligence/contexts/mentor-context/types'
import { Button } from '@/ui/shadcn/button'
import { Icon } from '@/ui/shared/widgets/components/icon'
import { MentorAttachmentPreview } from '@/ui/intelligence/widgets/components/mentor-attachment-preview'

type AttachmentListProps = {
  attachments: MentorDraftAttachment[]
  disabled: boolean
  onRemove(localKey: string): void
  onRetry?(localKey: string): void
}

const STATUS_LABELS = {
  uploading: 'Enviando arquivo…',
  processing: 'Preparando arquivo…',
  ready: 'Arquivo pronto',
  partial: 'Leitura parcial',
  failed: 'Falha na preparação',
  removed: 'Arquivo removido',
} as const

function formatSize(sizeBytes: number) {
  return sizeBytes < 1_000_000
    ? `${Math.max(1, Math.round(sizeBytes / 1_000))} KB`
    : `${(sizeBytes / 1_000_000).toFixed(1).replace('.', ',')} MB`
}

export const AttachmentList = ({
  attachments,
  disabled,
  onRemove,
  onRetry,
}: AttachmentListProps) => {
  if (attachments.length === 0) return null

  return (
    <ul aria-label='Arquivos anexados' className='space-y-2'>
      {attachments.map((draftAttachment) => {
        const attachment = draftAttachment.attachment
        const status = draftAttachment.error
          ? draftAttachment.error
          : attachment
            ? STATUS_LABELS[attachment.status]
            : 'Aguardando envio…'
        return (
          <li
            className='flex min-w-0 items-start gap-3 rounded-md border border-border bg-surface-alt p-3'
            key={draftAttachment.localKey}
          >
            {draftAttachment.previewUrl ? (
              <div className='w-20 shrink-0'>
                <MentorAttachmentPreview
                  filename={draftAttachment.file.name}
                  mediaType={attachment?.mediaType ?? draftAttachment.file.type}
                  src={draftAttachment.previewUrl}
                />
              </div>
            ) : null}
            <div className='min-w-0 flex-1 space-y-1'>
              <p
                className='break-all text-sm font-medium'
                title={draftAttachment.file.name}
              >
                {draftAttachment.file.name}
              </p>
              <p className='text-xs text-muted-foreground'>
                {(
                  attachment?.mediaType ||
                  draftAttachment.file.type ||
                  'Arquivo'
                ).toUpperCase()}
                {' · '}
                {formatSize(draftAttachment.file.size)}
              </p>
              <p
                aria-live={draftAttachment.error ? undefined : 'polite'}
                className={`text-xs ${draftAttachment.error ? 'text-destructive' : 'text-muted-foreground'}`}
                role={draftAttachment.error ? 'alert' : 'status'}
              >
                {status}
              </p>
              {attachment?.status === 'partial' ? (
                <p className='text-xs text-muted-foreground'>
                  {attachment.analyzedPages.length > 0
                    ? `Páginas analisadas: ${attachment.analyzedPages.join(', ')}.`
                    : 'Parte do conteúdo não pôde ser interpretada.'}
                  {attachment.illegiblePages.length > 0
                    ? ` Páginas ilegíveis: ${attachment.illegiblePages.join(', ')}.`
                    : ''}
                  {attachment.uninterpretedPages.length > 0
                    ? ` Páginas não analisadas: ${attachment.uninterpretedPages.join(', ')}.`
                    : ''}
                </p>
              ) : null}
            </div>
            {draftAttachment.retryable && onRetry ? (
              <Button
                className='min-h-11 shrink-0'
                disabled={disabled}
                onClick={() => onRetry(draftAttachment.localKey)}
                type='button'
                variant='default'
              >
                Tentar novamente
              </Button>
            ) : null}
            <Button
              aria-label={`Remover ${draftAttachment.file.name}`}
              className='size-11 shrink-0 px-0'
              disabled={disabled}
              onClick={() => onRemove(draftAttachment.localKey)}
              title={`Remover ${draftAttachment.file.name}`}
              type='button'
              variant='ghost'
            >
              <Icon className='size-4' name='x' />
            </Button>
          </li>
        )
      })}
    </ul>
  )
}
