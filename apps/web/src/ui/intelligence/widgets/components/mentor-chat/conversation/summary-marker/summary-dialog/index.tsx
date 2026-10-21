import { Button } from '@/ui/shadcn/button'
import {
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/ui/shadcn/dialog'
import { Icon } from '@/ui/shared/widgets/components/icon'

export type SummaryDialogProps = {
  summaryText: string | null
  isLoading: boolean
  hasError: boolean
  onRetry(): void
  onRevealOriginals(): void
  onCloseAutoFocus(event: Event): void
}

export const SummaryDialog = ({
  summaryText,
  isLoading,
  hasError,
  onRetry,
  onRevealOriginals,
  onCloseAutoFocus,
}: SummaryDialogProps) => (
  <DialogContent
    className='flex max-h-[calc(100dvh-2rem)] w-[calc(100%-2rem)]! flex-col bg-surface-alt! p-4! sm:p-6!'
    onCloseAutoFocus={onCloseAutoFocus}
  >
    <DialogClose
      aria-label='Fechar'
      className='absolute right-4 top-4 inline-flex size-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-white/5 hover:text-foreground'
      type='button'
    >
      <Icon className='size-4' name='x' />
    </DialogClose>
    <DialogHeader className='mb-4! shrink-0 border-b border-border pb-4 text-left!'>
      <div className='flex items-start gap-3 pr-10'>
        <div className='flex size-11 shrink-0 items-center justify-center rounded-full bg-accent'>
          <Icon className='size-5 text-selo-text' name='scroll-text' />
        </div>
        <div className='flex min-w-0 flex-col gap-1'>
          <DialogTitle className='text-lg font-semibold leading-snug text-foreground'>
            Resumo desta conversa
          </DialogTitle>
          <DialogDescription className='text-sm text-muted-foreground'>
            Suas mensagens originais continuam disponíveis.
          </DialogDescription>
        </div>
      </div>
    </DialogHeader>
    <div className='min-h-0 flex-1 overflow-y-auto'>
      {summaryText ? (
        <p className='whitespace-pre-wrap break-words text-sm leading-6 text-foreground'>
          {summaryText}
        </p>
      ) : hasError ? (
        <div className='space-y-3 text-sm' role='alert'>
          <p>Não foi possível carregar o resumo. Tente novamente.</p>
          <Button
            className='w-full border border-control-border! text-foreground! sm:w-auto'
            onClick={onRetry}
            type='button'
            variant='ghost'
          >
            Tentar novamente
          </Button>
        </div>
      ) : isLoading ? (
        <output className='block text-sm text-muted-foreground'>
          Carregando resumo…
        </output>
      ) : null}
    </div>
    <DialogFooter className='mt-6! shrink-0 flex-col! gap-2 border-t-0! pt-0! sm:flex-row! sm:justify-start! sm:space-x-0!'>
      <Button
        className='w-full border border-control-border! text-foreground! sm:w-auto'
        disabled={!summaryText}
        onClick={onRevealOriginals}
        type='button'
        variant='ghost'
      >
        Ver mensagens originais
      </Button>
      <DialogClose asChild>
        <Button
          className='w-full border border-control-border! text-foreground! sm:w-auto'
          type='button'
          variant='ghost'
        >
          Fechar resumo
        </Button>
      </DialogClose>
    </DialogFooter>
  </DialogContent>
)
