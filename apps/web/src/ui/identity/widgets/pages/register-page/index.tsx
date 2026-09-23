import { Anchor } from '@/ui/shared/widgets/components/anchor'
import { Icon } from '@/ui/shared/widgets/components/icon'
import { Button } from '@/ui/shadcn/button'
import { Input } from '@/ui/shadcn/input'
import { Label } from '@/ui/shadcn/label'

import { useRegisterPage } from './use-register-page'

export const RegisterPage = () => {
  const { alertRef, form, isSubmitting, message, submit } = useRegisterPage()

  return (
    <div className='relative isolate flex min-h-dvh w-full items-center justify-center overflow-x-hidden px-5 py-8 sm:py-12'>
      <main className='relative z-10 flex w-full max-w-[440px] flex-col rounded-2xl border border-border bg-card p-6 sm:p-8'>
        <div className='mb-8 text-center'>
          <p className='font-serif text-3xl leading-none text-foreground'>
            Shifu <span className='text-primary'>師</span>
          </p>
          <h1 className='mt-8 font-serif text-3xl font-normal text-foreground'>
            Criar conta
          </h1>
        </div>
        <form
          aria-label='Criar conta no Shifu'
          className='flex flex-col gap-5'
          noValidate
          onSubmit={submit}
        >
          <form.Field name='displayName'>
            {(field) => (
              <div className='flex flex-col gap-2'>
                <Label htmlFor='register-name'>Nome de exibição</Label>
                <Input
                  autoComplete='name'
                  disabled={isSubmitting}
                  id='register-name'
                  name={field.name}
                  onBlur={field.handleBlur}
                  onChange={(event) => field.handleChange(event.target.value)}
                  required
                  value={field.state.value}
                />
                {field.state.meta.errors[0] && (
                  <p className='text-sm text-selo-text'>
                    {String(field.state.meta.errors[0])}
                  </p>
                )}
              </div>
            )}
          </form.Field>
          <form.Field name='email'>
            {(field) => (
              <div className='flex flex-col gap-2'>
                <Label htmlFor='register-email'>E-mail</Label>
                <Input
                  autoComplete='email'
                  disabled={isSubmitting}
                  id='register-email'
                  name={field.name}
                  onBlur={field.handleBlur}
                  onChange={(event) => field.handleChange(event.target.value)}
                  placeholder='voce@exemplo.com'
                  required
                  type='email'
                  value={field.state.value}
                />
                {field.state.meta.errors[0] && (
                  <p className='text-sm text-selo-text'>
                    {String(field.state.meta.errors[0])}
                  </p>
                )}
              </div>
            )}
          </form.Field>
          <form.Field name='password'>
            {(field) => (
              <div className='flex flex-col gap-2'>
                <Label htmlFor='register-password'>Senha</Label>
                <Input
                  autoComplete='new-password'
                  disabled={isSubmitting}
                  id='register-password'
                  minLength={8}
                  name={field.name}
                  onBlur={field.handleBlur}
                  onChange={(event) => field.handleChange(event.target.value)}
                  required
                  type='password'
                  value={field.state.value}
                />
                <p className='text-sm text-muted-foreground'>
                  Use pelo menos 8 caracteres.
                </p>
                {field.state.meta.errors[0] && (
                  <p className='text-sm text-selo-text'>
                    {String(field.state.meta.errors[0])}
                  </p>
                )}
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
            {isSubmitting ? 'Criando conta...' : 'Criar conta'}
          </Button>
        </form>
        <p className='mt-6 text-center text-sm text-muted-foreground'>
          Já tem uma conta?{' '}
          <Anchor
            className='min-h-11 rounded-md px-1 py-3 underline-offset-4 hover:text-foreground hover:underline'
            route='login'
          >
            Entrar
          </Anchor>
        </p>
      </main>
    </div>
  )
}
