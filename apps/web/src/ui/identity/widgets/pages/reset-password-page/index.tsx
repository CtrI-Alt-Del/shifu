import { Anchor } from '@/ui/shared/widgets/components/anchor'

import { ResetPasswordForm } from './reset-form'
import { ResetPasswordLinkOutcome } from './link-outcome'
import { useResetPasswordPage } from './use-reset-password-page'

export type ResetPasswordPageProps = { token?: string }

export const ResetPasswordPage = ({ token }: ResetPasswordPageProps) => {
  const {
    confirmationError,
    handleContinue,
    handleRetry,
    handleRequestNewLink,
    headingRef,
    isPasswordVisible,
    isSubmitting,
    message,
    password,
    passwordConfirmation,
    passwordError,
    requiresEmailConfirmation,
    result,
    setPassword,
    setPasswordConfirmation,
    setPasswordVisible,
    submit,
  } = useResetPasswordPage(token)

  return (
    <div className='relative isolate mx-auto flex min-h-dvh w-full max-w-7xl items-center justify-center overflow-x-hidden px-5 py-8 sm:py-12'>
      <main className='relative z-10 flex w-full max-w-[440px] flex-col rounded-2xl border border-border bg-card p-6 sm:p-8'>
        <div className='mb-8 text-center'>
          <p className='font-serif text-3xl leading-none text-foreground'>
            Shifu <span className='text-primary'>師</span>
          </p>
          <h1 className='mt-8 font-serif text-3xl font-normal text-foreground'>
            Redefinir senha
          </h1>
          {result === 'form' && (
            <p className='mt-3 text-muted-foreground'>
              Escolha uma nova senha para continuar no Shifu.
            </p>
          )}
        </div>

        {result === 'form' ? (
          <ResetPasswordForm
            confirmationError={confirmationError}
            isPasswordVisible={isPasswordVisible}
            isSubmitting={isSubmitting}
            message={message}
            onPasswordChange={setPassword}
            onPasswordConfirmationChange={setPasswordConfirmation}
            onSetPasswordVisible={setPasswordVisible}
            onSubmit={submit}
            password={password}
            passwordConfirmation={passwordConfirmation}
            passwordError={passwordError}
          />
        ) : (
          <ResetPasswordLinkOutcome
            headingRef={headingRef}
            message={message}
            onContinue={handleContinue}
            onRetry={handleRetry}
            onRequestNewLink={handleRequestNewLink}
            requiresEmailConfirmation={requiresEmailConfirmation}
            result={result}
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
