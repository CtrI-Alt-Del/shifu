import { Button } from '@/ui/shadcn/button'
import { Anchor } from '@/ui/shared/widgets/components/anchor'
import { Icon } from '@/ui/shared/widgets/components/icon'

import { usePendingConfirmationPage } from './use-pending-confirmation-page'

export const PendingConfirmationPage = () => {
  const {
    alertRef,
    exitErrorMessage,
    handleExit,
    handleResend,
    isExiting,
    isLoading,
    isResending,
    message,
    remainingSeconds,
    state,
  } = usePendingConfirmationPage()
  const isCooldown = remainingSeconds > 0

  return (
    <div className='relative isolate flex min-h-dvh w-full items-center justify-center overflow-x-hidden px-5 py-8 sm:py-12'>
      <main className='relative z-10 flex w-full max-w-[440px] flex-col rounded-2xl border border-border bg-card p-6 text-center sm:p-8'>
        <p className='font-serif text-3xl leading-none text-foreground'>
          Shifu <span className='text-primary'>師</span>
        </p>
        <Icon className='mx-auto mt-8 text-success' name='circle-alert' size={32} />
        <h1 className='mt-4 font-serif text-3xl font-normal text-foreground'>
          Confirme seu e-mail
        </h1>
        <p className='mt-3 text-muted-foreground'>
          O restante do Shifu fica disponível depois que você confirmar seu e-mail.
        </p>
        {(message || exitErrorMessage) && (
          <div
            aria-live='assertive'
            className='mt-6 flex items-start gap-2 rounded-md border border-selo-text bg-accent px-3 py-2 text-left text-sm text-selo-text'
            ref={alertRef}
            role='alert'
            tabIndex={-1}
          >
            <Icon className='mt-0.5 shrink-0' name='circle-alert' size={16} />
            <span>{exitErrorMessage ?? message}</span>
          </div>
        )}
        <Button
          aria-busy={isResending || isLoading}
          className='mt-8'
          disabled={isCooldown || isResending || isLoading}
          onClick={handleResend}
          type='button'
        >
          {isResending
            ? 'Reenviando...'
            : isCooldown
              ? `Reenviar link em ${remainingSeconds}s`
              : 'Reenviar link'}
        </Button>
        {state === 'delivery_issue' && (
          <p className='mt-3 text-sm text-muted-foreground'>
            Se não encontrar a mensagem, aguarde um momento e tente reenviar.
          </p>
        )}
        <Button
          aria-busy={isExiting}
          className='mt-3 border border-selo-text text-selo-text hover:bg-accent hover:text-selo-text'
          disabled={isExiting}
          onClick={handleExit}
          type='button'
          variant='ghost'
        >
          {isExiting && (
            <Icon className='mr-2 animate-spin' name='loader-circle' size={16} />
          )}
          {isExiting ? 'Saindo...' : 'Sair'}
        </Button>
        <Anchor
          className='mt-6 min-h-11 rounded-md px-1 py-3 text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline'
          route='login'
        >
          Voltar para entrar
        </Anchor>
      </main>
    </div>
  )
}
