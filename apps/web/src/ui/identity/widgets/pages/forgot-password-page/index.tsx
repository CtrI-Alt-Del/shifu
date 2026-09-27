import { Anchor } from '@/ui/shared/widgets/components/anchor'

import { ForgotPasswordRequestStatus } from './request-status'
import { ForgotPasswordRequestForm } from './request-form'
import { useForgotPasswordPage } from './use-forgot-password-page'

export const ForgotPasswordPage = () => {
  const {
    email,
    emailError,
    handleRetry,
    handleStartOver,
    isRetrying,
    isSubmitting,
    message,
    mode,
    retryAfterSeconds,
    setEmail,
    status,
    statusRef,
    submit,
  } = useForgotPasswordPage()

  return (
    <div className='relative isolate mx-auto flex min-h-dvh w-full max-w-7xl items-center justify-center overflow-x-hidden px-5 py-8 sm:py-12'>
      <main className='relative z-10 flex w-full max-w-[440px] flex-col rounded-2xl border border-border bg-card p-6 sm:p-8'>
        <div className='mb-8 text-center'>
          <p className='font-serif text-3xl leading-none text-foreground'>
            Shifu <span className='text-primary'>師</span>
          </p>
          <h1 className='mt-8 font-serif text-3xl font-normal text-foreground'>
            Esqueci minha senha
          </h1>
          <p className='mt-3 text-muted-foreground'>
            Informe seu e-mail para receber um link seguro de recuperação.
          </p>
        </div>

        {mode === 'form' ? (
          <ForgotPasswordRequestForm
            email={email}
            emailError={emailError}
            isSubmitting={isSubmitting}
            message={message}
            onEmailChange={setEmail}
            onSubmit={submit}
          />
        ) : (
          <ForgotPasswordRequestStatus
            isRetrying={isRetrying}
            message={message}
            onRetry={handleRetry}
            onStartOver={handleStartOver}
            retryAfterSeconds={retryAfterSeconds}
            status={status}
            statusRef={statusRef}
          />
        )}

        <nav aria-label='Opções de acesso' className='mt-6 text-center text-sm'>
          <Anchor
            className='min-h-11 rounded-md px-1 py-3 text-muted-foreground underline-offset-4 hover:text-foreground hover:underline'
            route='login'
          >
            Voltar para entrar
          </Anchor>
        </nav>
      </main>
    </div>
  )
}
