import { Anchor } from '@/ui/shared/widgets/components/anchor'
import { Icon } from '@/ui/shared/widgets/components/icon'
import { Button } from '@/ui/shadcn/button'

import { useConfirmEmailPage } from './use-confirm-email-page'

export type ConfirmEmailPageProps = { token?: string }

export const ConfirmEmailPage = ({ token }: ConfirmEmailPageProps) => {
  const { content, handleContinue, headingRef, redirectTo, result } =
    useConfirmEmailPage(token)
  return (
    <div className='relative isolate flex min-h-dvh w-full items-center justify-center overflow-x-hidden px-5 py-8 sm:py-12'>
      <main className='relative z-10 flex w-full max-w-[440px] flex-col items-center rounded-2xl border border-border bg-card p-6 text-center sm:p-8'>
        <Icon
          className={content.success ? 'text-success' : 'text-selo-text'}
          name='circle-alert'
          size={32}
        />
        <h1
          className='mt-5 font-serif text-3xl font-normal text-foreground'
          ref={headingRef}
          tabIndex={-1}
        >
          {content.title}
        </h1>
        <p className='mt-3 text-muted-foreground'>{content.description}</p>
        {result === 'loading' ? (
          <p aria-live='polite' className='mt-8 text-sm text-muted-foreground'>
            Confirmando seu e-mail...
          </p>
        ) : result === 'unavailable' ? (
          <Anchor
            className='mt-8 min-h-11 rounded-md px-1 py-3 text-muted-foreground underline-offset-4 hover:text-foreground hover:underline'
            route='login'
          >
            Entrar
          </Anchor>
        ) : (
          <Button className='mt-8 w-full' onClick={handleContinue} type='button'>
            {redirectTo === 'root' ? 'Continuar' : 'Entrar'}
          </Button>
        )}
      </main>
    </div>
  )
}
