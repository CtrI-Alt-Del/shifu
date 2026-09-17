import { Anchor } from '@/ui/shared/widgets/components/anchor'
import { Icon } from '@/ui/shared/widgets/components/icon'
import { Button } from '@/ui/shadcn/button'
import { Input } from '@/ui/shadcn/input'
import { Label } from '@/ui/shadcn/label'

import { useSignInPage } from './use-sign-in-page'

export const SignInPage = () => {
  const {
    alertRef,
    form,
    isPasswordVisible,
    isSubmitting,
    message,
    setPasswordVisible,
    submit,
  } = useSignInPage()

  return (
    <div className='relative isolate flex min-h-dvh w-full items-center justify-center overflow-x-hidden px-5 py-8 sm:py-12'>
      <main className='relative z-10 flex w-full max-w-[440px] flex-col rounded-2xl border border-border bg-card p-6 sm:p-8'>
        <div className='mb-8 text-center'>
          <p className='font-serif text-3xl leading-none text-foreground'>
            Shifu <span className='text-primary'>師</span>
          </p>
          <h1 className='mt-8 font-serif text-3xl font-normal text-foreground'>Entrar</h1>
        </div>

        <form
          aria-label='Entrar no Shifu'
          className='flex flex-col gap-5'
          onSubmit={submit}
        >
          <form.Field name='email'>
            {(field) => (
              <div className='flex flex-col gap-2'>
                <Label htmlFor='sign-in-email'>E-mail</Label>
                <Input
                  autoComplete='email'
                  disabled={isSubmitting}
                  id='sign-in-email'
                  name={field.name}
                  onBlur={field.handleBlur}
                  onChange={(event) => field.handleChange(event.target.value)}
                  placeholder='voce@exemplo.com'
                  required
                  type='email'
                  value={field.state.value}
                />
              </div>
            )}
          </form.Field>

          <form.Field name='password'>
            {(field) => (
              <div className='flex flex-col gap-2'>
                <Label htmlFor='sign-in-password'>Senha</Label>
                <div className='relative'>
                  <Input
                    autoComplete='current-password'
                    className='pr-12'
                    disabled={isSubmitting}
                    id='sign-in-password'
                    name={field.name}
                    onBlur={field.handleBlur}
                    onChange={(event) => field.handleChange(event.target.value)}
                    placeholder='••••••••'
                    required
                    type={isPasswordVisible ? 'text' : 'password'}
                    value={field.state.value}
                  />
                  <Button
                    aria-label={isPasswordVisible ? 'Ocultar senha' : 'Mostrar senha'}
                    className='absolute right-0 top-1/2 size-11 -translate-y-1/2 px-0'
                    disabled={isSubmitting}
                    onClick={() => setPasswordVisible((visible) => !visible)}
                    type='button'
                    variant='ghost'
                  >
                    <Icon name={isPasswordVisible ? 'eye-off' : 'eye'} size={18} />
                  </Button>
                </div>
              </div>
            )}
          </form.Field>

          {message && (
            <div
              aria-live='assertive'
              className='flex items-start gap-2 rounded-md border border-selo-text bg-accent px-3 py-2 text-sm text-selo-text'
              ref={alertRef}
              role='alert'
              tabIndex={-1}
            >
              <Icon className='mt-0.5 shrink-0' name='circle-alert' size={16} />
              <span>{message}</span>
            </div>
          )}

          <Button aria-busy={isSubmitting} disabled={isSubmitting} type='submit'>
            {isSubmitting && (
              <Icon className='animate-spin' name='loader-circle' size={16} />
            )}
            {isSubmitting ? 'Entrando...' : 'Entrar'}
          </Button>
        </form>

        <nav
          aria-label='Opções de acesso'
          className='mt-6 flex items-center justify-between gap-3 text-sm'
        >
          <Anchor
            className='min-h-11 rounded-md px-1 py-3 text-muted-foreground underline-offset-4 hover:text-foreground hover:underline'
            route='forgotPassword'
          >
            Esqueci minha senha
          </Anchor>
          <Anchor
            className='min-h-11 rounded-md px-1 py-3 text-muted-foreground underline-offset-4 hover:text-foreground hover:underline'
            route='register'
          >
            Criar conta
          </Anchor>
        </nav>
      </main>
    </div>
  )
}
