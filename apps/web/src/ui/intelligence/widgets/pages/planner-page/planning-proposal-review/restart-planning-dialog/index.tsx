import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogTitle,
} from '@/ui/shadcn/alert-dialog'
import { Button } from '@/ui/shadcn/button'
import { Label } from '@/ui/shadcn/label'
import { Textarea } from '@/ui/shadcn/textarea'
import { Icon } from '@/ui/shared/widgets/components/icon'

import {
  type RestartPlanningDialogProps,
  useRestartPlanningDialog,
} from './use-restart-planning-dialog'

export type { RestartPlanningDialogProps } from './use-restart-planning-dialog'

export const RestartPlanningDialog = (props: RestartPlanningDialogProps) => {
  const { isOpen, isSubmitting, errorMessage, restoreFocusRef, onClose } = props
  const {
    intent,
    validationMessage,
    textareaRef,
    handleIntentChange,
    handleSubmit,
    handleOpenAutoFocus,
  } = useRestartPlanningDialog(props)
  const messageId = validationMessage
    ? 'restart-planning-intent-validation'
    : errorMessage
      ? 'restart-planning-intent-error'
      : undefined

  return (
    <AlertDialog
      onOpenChange={(open) => {
        if (!open) onClose()
      }}
      open={isOpen}
    >
      <AlertDialogContent
        className='max-w-[600px]! rounded-[14px]! border-border! bg-surface-alt! p-5! sm:p-6!'
        onCloseAutoFocus={(event) => {
          if (!restoreFocusRef.current) return

          event.preventDefault()
          restoreFocusRef.current.focus()
        }}
        onOpenAutoFocus={handleOpenAutoFocus}
      >
        <form className='flex flex-col gap-5 sm:gap-6' noValidate onSubmit={handleSubmit}>
          <div className='flex items-start justify-between gap-4'>
            <AlertDialogTitle className='font-serif text-[26px] leading-tight text-foreground sm:text-3xl'>
              Reiniciar planejamento
            </AlertDialogTitle>
            <button
              aria-label='Fechar'
              className='grid size-11 shrink-0 place-items-center rounded-md text-secondary-foreground transition-colors hover:bg-white/5 hover:text-foreground sm:size-9'
              disabled={isSubmitting}
              onClick={onClose}
              type='button'
            >
              <Icon name='x' size={20} />
            </button>
          </div>
          <div className='flex flex-col gap-2'>
            <Label className='text-sm font-semibold' htmlFor='restart-planning-intent'>
              O que você quer aprender?
            </Label>
            <Textarea
              aria-describedby={messageId}
              aria-invalid={Boolean(validationMessage)}
              className='min-h-36 resize-none px-4 py-4 text-[15px] leading-[1.5]'
              disabled={isSubmitting}
              id='restart-planning-intent'
              onChange={(event) => handleIntentChange(event.target.value)}
              ref={textareaRef}
              rows={4}
              value={intent}
            />
            {validationMessage ? (
              <p
                className='flex items-center gap-2 text-sm text-selo-text'
                id='restart-planning-intent-validation'
                role='alert'
              >
                <Icon className='shrink-0' name='circle-alert' size={16} />
                {validationMessage}
              </p>
            ) : null}
            {errorMessage && !validationMessage ? (
              <p
                className='flex items-center gap-2 text-sm text-selo-text'
                id='restart-planning-intent-error'
                role='alert'
              >
                <Icon className='shrink-0' name='circle-alert' size={16} />
                {errorMessage}
              </p>
            ) : null}
          </div>
          <AlertDialogDescription className='text-[13px] leading-[1.5] text-secondary-foreground'>
            Ao continuar, a proposta e as respostas anteriores serão substituídas por um
            novo planejamento.
          </AlertDialogDescription>
          <div className='flex justify-end'>
            <Button
              aria-busy={isSubmitting}
              className='w-full gap-1.5 sm:w-auto lg:min-h-[38px] lg:px-[18px] lg:text-sm'
              disabled={isSubmitting}
              type='submit'
            >
              {isSubmitting ? (
                <Icon className='animate-spin' name='loader-circle' size={16} />
              ) : null}
              {isSubmitting ? 'Iniciando…' : 'Iniciar planejamento'}
            </Button>
          </div>
        </form>
      </AlertDialogContent>
    </AlertDialog>
  )
}
