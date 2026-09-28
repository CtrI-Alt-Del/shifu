import { Button } from '@/ui/shadcn/button'
import { Icon } from '@/ui/shared/widgets/components/icon'
import { Input } from '@/ui/shadcn/input'
import { Label } from '@/ui/shadcn/label'

export type ResetPasswordFormProps = {
  confirmationError: string | null
  isPasswordVisible: boolean
  isSubmitting: boolean
  message: string | null
  onPasswordChange: (value: string) => void
  onPasswordConfirmationChange: (value: string) => void
  onSetPasswordVisible: (value: boolean) => void
  onSubmit: React.FormEventHandler<HTMLFormElement>
  password: string
  passwordConfirmation: string
  passwordError: string | null
}

export const ResetPasswordForm = ({
  confirmationError,
  isPasswordVisible,
  isSubmitting,
  message,
  onPasswordChange,
  onPasswordConfirmationChange,
  onSetPasswordVisible,
  onSubmit,
  password,
  passwordConfirmation,
  passwordError,
}: ResetPasswordFormProps) => {
  return (
    <form
      aria-label='Redefinir senha'
      className='flex flex-col gap-5'
      noValidate
      onSubmit={onSubmit}
    >
      <div className='flex flex-col gap-2'>
        <Label htmlFor='reset-password-password'>Nova senha</Label>
        <div className='relative'>
          <Input
            aria-describedby={passwordError ? 'reset-password-password-error' : undefined}
            aria-invalid={passwordError ? true : undefined}
            autoComplete='new-password'
            className='pr-12'
            disabled={isSubmitting}
            id='reset-password-password'
            minLength={8}
            onChange={(event) => onPasswordChange(event.target.value)}
            placeholder='••••••••'
            required
            type={isPasswordVisible ? 'text' : 'password'}
            value={password}
          />
          <Button
            aria-label={isPasswordVisible ? 'Ocultar senha' : 'Mostrar senha'}
            className='absolute right-0 top-1/2 size-11 -translate-y-1/2 px-0'
            disabled={isSubmitting}
            onClick={() => onSetPasswordVisible(!isPasswordVisible)}
            type='button'
            variant='ghost'
          >
            <Icon name={isPasswordVisible ? 'eye-off' : 'eye'} size={18} />
          </Button>
        </div>
        <p className='text-sm text-muted-foreground'>Use pelo menos 8 caracteres.</p>
        {passwordError && (
          <p className='text-sm text-selo-text' id='reset-password-password-error'>
            {passwordError}
          </p>
        )}
      </div>

      <div className='flex flex-col gap-2'>
        <Label htmlFor='reset-password-confirmation'>Confirmar nova senha</Label>
        <Input
          aria-describedby={
            confirmationError ? 'reset-password-confirmation-error' : undefined
          }
          aria-invalid={confirmationError ? true : undefined}
          autoComplete='new-password'
          disabled={isSubmitting}
          id='reset-password-confirmation'
          onChange={(event) => onPasswordConfirmationChange(event.target.value)}
          placeholder='••••••••'
          required
          type={isPasswordVisible ? 'text' : 'password'}
          value={passwordConfirmation}
        />
        {confirmationError && (
          <p className='text-sm text-selo-text' id='reset-password-confirmation-error'>
            {confirmationError}
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
        {isSubmitting && <Icon className='animate-spin' name='loader-circle' size={16} />}
        {isSubmitting ? 'Redefinindo...' : 'Redefinir senha'}
      </Button>
    </form>
  )
}
