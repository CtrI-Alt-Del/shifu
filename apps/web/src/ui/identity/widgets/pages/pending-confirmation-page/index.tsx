import { Button } from '@/ui/shadcn/button'
import { Icon } from '@/ui/shared/widgets/components/icon'

import { usePendingConfirmationPage } from './use-pending-confirmation-page'

export const PendingConfirmationPage = () => {
  const { alertRef, errorMessage, handleExit, isExiting, status } =
    usePendingConfirmationPage()

  return (
    <div className='relative isolate flex min-h-dvh w-full items-center justify-center overflow-x-hidden px-5 py-8 sm:py-12'>
      <main className='relative z-10 flex w-full max-w-[440px] flex-col rounded-2xl border border-border bg-card p-6 sm:p-8'>
        <div className='mb-8 text-center'>
          <p className='font-serif text-3xl leading-none text-foreground'>
            Shifu <span className='text-primary'>師</span>
          </p>
          <h1 className='mt-8 font-serif text-3xl font-normal text-foreground'>
            Aguardando confirmação
          </h1>
        </div>

        <div className='flex flex-col gap-4'>
          <p className='leading-7 text-muted-foreground'>
            Confirme seu e-mail para liberar o restante do Shifu. Depois de confirmar,
            volte para entrar e continuar sua jornada.
          </p>

          {status === 'success' && (
            <output
              aria-live='polite'
              className='flex items-start gap-2 rounded-md border border-success bg-muted px-3 py-2 text-sm text-success'
            >
              <Icon className='mt-0.5 shrink-0' name='circle-check' size={16} />
              <span>Saída concluída. Redirecionando para Entrar...</span>
            </output>
          )}

          {errorMessage && (
            <div
              aria-live='assertive'
              className='flex items-start gap-2 rounded-md border border-selo-text bg-accent px-3 py-2 text-sm text-selo-text'
              ref={alertRef}
              role='alert'
              tabIndex={-1}
            >
              <Icon className='mt-0.5 shrink-0' name='circle-alert' size={16} />
              <span>{errorMessage}</span>
            </div>
          )}

          {status !== 'success' && (
            <Button
              aria-busy={isExiting}
              className='self-start border border-selo-text text-selo-text hover:bg-accent hover:text-selo-text'
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
          )}
        </div>
      </main>
    </div>
  )
}
