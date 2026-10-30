import { Button } from '@/ui/shadcn/button'
import { Input } from '@/ui/shadcn/input'
import { Label } from '@/ui/shadcn/label'
import { useSecurityForm } from './use-security-form'

export const SecurityForm = () => {
  const {
    alertRef,
    currentPassword,
    newPassword,
    errors,
    isPending,
    isSuccess,
    isPasswordVisible,
    message,
    handleCurrentPasswordChange,
    handleNewPasswordChange,
    handleTogglePasswordVisibility,
    handleSubmit,
  } = useSecurityForm()
  return (
    <form
      method='post'
      aria-labelledby='account-security-title'
      aria-busy={isPending}
      className='space-y-4 rounded-lg border border-border bg-card p-6'
      onSubmit={handleSubmit}
      noValidate
    >
      <h2 id='account-security-title' className='text-base font-semibold'>
        Alterar senha
      </h2>
      <div className='space-y-2 pt-5'>
        <Label htmlFor='account-current-password'>Senha atual</Label>
        <Input
          id='account-current-password'
          type={isPasswordVisible ? 'text' : 'password'}
          autoComplete='current-password'
          value={currentPassword}
          onChange={(event) => handleCurrentPasswordChange(event.target.value)}
          disabled={isPending}
          aria-invalid={Boolean(errors.currentPassword)}
          aria-describedby={
            errors.currentPassword ? 'account-current-password-error' : undefined
          }
          className='min-h-[52px]'
        />
        {errors.currentPassword && (
          <p id='account-current-password-error' className='text-sm text-selo-text'>
            {errors.currentPassword}
          </p>
        )}
      </div>
      <div className='space-y-2'>
        <Label htmlFor='account-new-password'>Nova senha · mínimo de 8 caracteres</Label>
        <Input
          id='account-new-password'
          type={isPasswordVisible ? 'text' : 'password'}
          autoComplete='new-password'
          value={newPassword}
          onChange={(event) => handleNewPasswordChange(event.target.value)}
          disabled={isPending}
          aria-invalid={Boolean(errors.newPassword)}
          aria-describedby={errors.newPassword ? 'account-new-password-error' : undefined}
          className='min-h-[52px]'
        />
        {errors.newPassword && (
          <p id='account-new-password-error' className='text-sm text-selo-text'>
            {errors.newPassword}
          </p>
        )}
      </div>
      <Button
        type='button'
        variant='ghost'
        className='px-0 text-xs'
        aria-pressed={isPasswordVisible}
        onClick={handleTogglePasswordVisibility}
      >
        {isPasswordVisible ? 'Ocultar senhas' : 'Mostrar senhas'}
      </Button>
      {message && (
        <p
          role={isSuccess ? 'status' : 'alert'}
          ref={alertRef}
          tabIndex={-1}
          className={`text-sm ${isSuccess ? 'text-jade-text' : 'text-selo-text'}`}
        >
          {message}
        </p>
      )}
      <div className='flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between'>
        <p className='text-xs leading-6 text-muted-foreground'>
          Os outros acessos serão encerrados. Este continua.
        </p>
        <Button type='submit' disabled={isPending} className='w-full text-sm sm:w-auto'>
          {isPending ? 'Alterando…' : 'Alterar senha'}
        </Button>
      </div>
    </form>
  )
}
