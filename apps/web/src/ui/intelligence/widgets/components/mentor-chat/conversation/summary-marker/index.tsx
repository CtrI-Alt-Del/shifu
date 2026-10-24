import { Button } from '@/ui/shadcn/button'
import { Dialog, DialogTrigger } from '@/ui/shadcn/dialog'
import { Icon } from '@/ui/shared/widgets/components/icon'

import { SummaryDialog } from './summary-dialog'
import { type SummaryMarkerProps, useSummaryMarker } from './use-summary-marker'

export type { SummaryMarkerProps }

export const SummaryMarker = (props: SummaryMarkerProps) => {
  const {
    isOpen,
    summaryText,
    isLoadingSummary,
    hasSummaryError,
    rootRef,
    triggerRef,
    handleOpenChange,
    handleCloseAutoFocus,
    handleRevealOriginals,
    handleRetry,
  } = useSummaryMarker(props)

  if (props.variant === 'processing')
    return (
      <output className='flex min-h-6 items-center gap-2 font-sans text-[13px] text-jade-text'>
        <Icon
          className='size-4 shrink-0 animate-spin motion-reduce:animate-none'
          name='loader-circle'
        />
        <span>Resumindo contexto…</span>
      </output>
    )

  if (props.variant === 'failed')
    return (
      <p className='flex items-start gap-2 font-sans text-[13px] text-muted-foreground'>
        <Icon className='mt-0.5 size-4 shrink-0' name='circle-alert' />
        <span>
          Não foi possível resumir o contexto. O histórico completo continua disponível.
        </span>
      </p>
    )

  return (
    <div
      className='flex min-h-11 flex-wrap items-center gap-x-2 font-sans text-[13px] text-muted-foreground'
      ref={rootRef}
    >
      <Icon className='size-4 shrink-0' name='scroll-text' />
      <span>Contexto resumido</span>
      <Dialog onOpenChange={handleOpenChange} open={isOpen}>
        <DialogTrigger asChild>
          <Button
            aria-haspopup='dialog'
            className='px-2 text-[13px] font-medium'
            ref={triggerRef}
            type='button'
            variant='ghost'
          >
            Ver resumo
          </Button>
        </DialogTrigger>
        <SummaryDialog
          hasError={hasSummaryError}
          isLoading={isLoadingSummary}
          onCloseAutoFocus={handleCloseAutoFocus}
          onRetry={handleRetry}
          onRevealOriginals={() => void handleRevealOriginals()}
          summaryText={summaryText}
        />
      </Dialog>
    </div>
  )
}
