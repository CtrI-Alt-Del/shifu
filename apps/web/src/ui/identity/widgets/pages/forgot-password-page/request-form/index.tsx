import { Button } from '@/ui/shadcn/button'
import { Input } from '@/ui/shadcn/input'
import { Label } from '@/ui/shadcn/label'

export type ForgotPasswordRequestFormProps = {
  email: string
  emailError: string | null
  isSubmitting: boolean
  message: string | null
  onEmailChange: (value: string) => void
  onSubmit: React.FormEventHandler<HTMLFormElement>
}

export const ForgotPasswordRequestForm = ({
  email,
  emailError,
  isSubmitting,
  message,
  onEmailChange,
  onSubmit,
}: ForgotPasswordRequestFormProps) => {
  return (
    <form
      aria-label='Solicitar recuperação de senha'
      className='flex flex-col gap-5'
      noValidate
      onSubmit={onSubmit}
    >
      <div className='flex flex-col gap-2'>
        <Label htmlFor='forgot-password-email'>E-mail</Label>
        <Input
          aria-describedby={emailError ? 'forgot-password-email-error' : undefined}
          aria-invalid={emailError ? true : undefined}
          autoComplete='email'
          disabled={isSubmitting}
          id='forgot-password-email'
          onChange={(event) => onEmailChange(event.target.value)}
          placeholder='voce@exemplo.com'
          required
          type='email'
          value={email}
        />
        {emailError && (
          <p className='text-sm text-selo-text' id='forgot-password-email-error'>
            {emailError}
          </p>
        )}
      </div>

      {message && (
        <div
          aria-live='assertive'
          className='rounded-md border border-selo-text bg-accent px-3 py-2 text-sm text-selo-text'
          role='alert'
        >
          {message}
        </div>
      )}

      <Button aria-busy={isSubmitting} disabled={isSubmitting} type='submit'>
        {isSubmitting ? 'Enviando...' : 'Enviar link de recuperação'}
      </Button>
    </form>
  )
}
