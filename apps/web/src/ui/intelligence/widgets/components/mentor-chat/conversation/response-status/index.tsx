import type { MentorResponseSnapshot } from '@/core/intelligence/mentor-response'
import { MotionConfig, motion } from 'motion/react'
import { Button } from '@/ui/shadcn/button'
import { Icon } from '@/ui/shared/widgets/components/icon'
export type ResponseStatusProps = {
  response: MentorResponseSnapshot
  isPending: boolean
  onCancel(): Promise<void>
  onRetry(): Promise<void>
  /** A quota block keeps the retry visible and focusable but inert. */
  isAiQuotaBlocked?: boolean
  /** Id of the quota blocked card that explains the disabled retry. */
  aiQuotaBlockedId?: string
}
const STATUS_LABELS = {
  queued: 'Aguardando resposta',
  processing: 'Preparando resposta',
  completed: 'Resposta concluída',
  failed: 'Não foi possível concluir a resposta',
  cancelled: 'Resposta cancelada',
}
const PROGRESS_LABELS = {
  'summarize-context': 'Resumindo contexto…',
  'write-answer': 'Gerando resposta',
  'review-answer': 'Revisando resposta',
}
export const ResponseStatus = ({
  response,
  isPending,
  onCancel,
  onRetry,
  isAiQuotaBlocked = false,
  aiQuotaBlockedId,
}: ResponseStatusProps) => (
  <div className='space-y-2 py-3 text-sm text-muted-foreground'>
    {response.status === 'queued' || response.status === 'processing' ? (
      <MotionConfig reducedMotion='user'>
        <div aria-hidden='true' className='flex h-5 items-center gap-1.5'>
          {[0, 1, 2].map((index) => (
            <motion.span
              animate={{ y: [0, -6, 0] }}
              className='size-2 shrink-0 rounded-full bg-primary'
              key={index}
              transition={{
                delay: index * 0.12,
                duration: 0.6,
                ease: 'easeInOut',
                repeat: Number.POSITIVE_INFINITY,
              }}
            />
          ))}
        </div>
      </MotionConfig>
    ) : null}
    <output
      className={response.status === 'failed' ? 'flex items-center gap-2' : 'block'}
    >
      {response.status === 'failed' ? (
        <Icon className='size-4 shrink-0 text-danger' name='circle-alert' />
      ) : null}
      {response.status === 'processing' && response.progress
        ? PROGRESS_LABELS[response.progress]
        : STATUS_LABELS[response.status]}
    </output>
    {response.status === 'queued' || response.status === 'processing' ? (
      <Button
        className='min-h-11'
        disabled={isPending}
        onClick={() => void onCancel()}
        variant='ghost'
      >
        Cancelar resposta
      </Button>
    ) : response.status === 'failed' || response.status === 'cancelled' ? (
      <Button
        aria-describedby={isAiQuotaBlocked ? aiQuotaBlockedId : undefined}
        aria-disabled={isAiQuotaBlocked || undefined}
        className={`min-h-11 px-3! ${isAiQuotaBlocked ? 'text-foreground!' : ''}`}
        disabled={isPending && !isAiQuotaBlocked}
        onClick={isAiQuotaBlocked ? undefined : () => void onRetry()}
        variant='ghost'
      >
        Tentar novamente
      </Button>
    ) : null}
  </div>
)
