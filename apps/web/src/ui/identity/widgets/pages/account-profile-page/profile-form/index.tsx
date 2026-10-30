import type { AccountProfile } from '@/provision/auth/cookie-session-auth-provider'
import { Button } from '@/ui/shadcn/button'
import { Input } from '@/ui/shadcn/input'
import { Label } from '@/ui/shadcn/label'
import { Select } from '@/ui/shadcn/select'
import { useProfileForm } from './use-profile-form'

export type ProfileFormProps = { profile: AccountProfile }

export const ProfileForm = (props: ProfileFormProps) => {
  const {
    alertRef,
    displayName,
    email,
    errors,
    isPending,
    isSuccess,
    isSuggestedTimeZone,
    message,
    refreshWarning,
    timeZone,
    timeZoneOptions,
    handleDisplayNameChange,
    handleTimeZoneChange,
    handleSubmit,
  } = useProfileForm(props)
  return (
    <form
      method='post'
      aria-label='Perfil da conta'
      aria-busy={isPending}
      className='space-y-4 rounded-lg border border-border bg-card p-6'
      onSubmit={handleSubmit}
      noValidate
    >
      <div className='space-y-2'>
        <Label htmlFor='account-name'>Nome de exibição</Label>
        <Input
          id='account-name'
          autoComplete='name'
          value={displayName}
          onChange={(event) => handleDisplayNameChange(event.target.value)}
          disabled={isPending}
          aria-invalid={Boolean(errors.displayName)}
          aria-describedby={errors.displayName ? 'account-name-error' : undefined}
          className='min-h-[52px]'
        />
        {errors.displayName && (
          <p id='account-name-error' className='text-sm text-selo-text'>
            {errors.displayName}
          </p>
        )}
      </div>
      <div className='space-y-2'>
        <Label htmlFor='account-email'>E-mail · não editável</Label>
        <Input
          id='account-email'
          autoComplete='email'
          value={email}
          readOnly
          className='min-h-[52px] bg-surface-alt text-muted-foreground'
        />
      </div>
      <div className='space-y-2'>
        <Label htmlFor='account-time-zone'>Fuso horário</Label>
        <Select
          id='account-time-zone'
          value={timeZone || null}
          options={timeZoneOptions}
          onValueChange={handleTimeZoneChange}
          disabled={isPending}
          required
          aria-invalid={Boolean(errors.timeZone)}
          aria-describedby='account-time-zone-help'
          placeholder='Selecione seu fuso horário'
          className='min-h-[52px]'
        />
        <p
          id='account-time-zone-help'
          className='text-xs leading-5 text-muted-foreground'
        >
          {errors.timeZone ??
            (isSuggestedTimeZone
              ? 'Sugestão do navegador. Este fuso ainda não foi salvo.'
              : 'O fuso organiza as próximas datas da sua conta.')}
        </p>
      </div>
      {message && (
        <p
          ref={alertRef}
          tabIndex={-1}
          role={isSuccess ? 'status' : 'alert'}
          className={`text-sm ${isSuccess ? 'text-jade-text' : 'text-selo-text'}`}
        >
          {message}
        </p>
      )}
      {refreshWarning && (
        <output className='block text-sm text-muted-foreground'>{refreshWarning}</output>
      )}
      <div className='flex justify-end'>
        <Button type='submit' disabled={isPending} className='w-full text-sm sm:w-auto'>
          {isPending ? 'Salvando…' : 'Salvar'}
        </Button>
      </div>
    </form>
  )
}
