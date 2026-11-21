import { STREAK_REMINDER_HOUR_OPTIONS } from '@/ui/gamification/constants/streak-reminder-hour-options'
import { Button } from '@/ui/shadcn/button'
import { Label } from '@/ui/shadcn/label'
import { Select } from '@/ui/shadcn/select'
import { Skeleton } from '@/ui/shadcn/skeleton'
import { Switch } from '@/ui/shadcn/switch'

import { BlockedNotice } from './blocked-notice'
import { useStreakReminderCard } from './use-streak-reminder-card'

export const StreakReminderCard = () => {
  const {
    hour,
    isLoading,
    hasError,
    isEnabled,
    isSwitching,
    isHourPending,
    notice,
    handleSwitchChange,
    handleHourChange,
    handleRetry,
  } = useStreakReminderCard()

  return (
    <section
      aria-busy={isLoading}
      aria-labelledby='streak-reminder-title'
      className='rounded-lg border border-border bg-card p-6'
    >
      <h2 id='streak-reminder-title' className='text-base font-semibold'>
        Lembrete de sequência
      </h2>
      {isLoading ? (
        <div className='mt-4 space-y-4'>
          <Skeleton className='h-5 w-full max-w-md' />
          <Skeleton className='h-11 w-36' />
          <Skeleton className='h-13 w-full' />
        </div>
      ) : hasError ? (
        <div className='mt-4' role='alert'>
          <p className='text-sm leading-6 text-muted-foreground'>
            Não foi possível carregar os lembretes agora.
          </p>
          <Button className='mt-4' onClick={handleRetry} type='button' variant='outline'>
            Tentar novamente
          </Button>
        </div>
      ) : (
        <div className='mt-4 flex flex-col gap-4'>
          <p
            className='text-sm leading-6 text-muted-foreground'
            id='streak-reminder-description'
          >
            Receba uma notificação no horário escolhido quando você ainda não praticou no
            dia, para não perder sua sequência.
          </p>
          <div className='flex min-h-11 items-center gap-3'>
            <Switch
              aria-describedby='streak-reminder-description'
              aria-labelledby='streak-reminder-title streak-reminder-switch-label'
              checked={isEnabled}
              disabled={isSwitching}
              id='streak-reminder-switch'
              onCheckedChange={handleSwitchChange}
            />
            <span
              className='text-sm font-semibold text-foreground'
              id='streak-reminder-switch-label'
            >
              {isEnabled ? 'Ativados' : 'Desativados'}
            </span>
          </div>
          {notice ? <BlockedNotice notice={notice} /> : null}
          <div className='space-y-2'>
            <Label className='block' htmlFor='streak-reminder-hour'>
              Horário do lembrete
            </Label>
            <Select
              aria-busy={isHourPending}
              aria-describedby='streak-reminder-hour-help'
              className='min-h-[52px]'
              id='streak-reminder-hour'
              onValueChange={handleHourChange}
              options={STREAK_REMINDER_HOUR_OPTIONS}
              readOnly={isHourPending}
              value={String(hour)}
            />
            <p
              className='text-xs leading-5 text-muted-foreground'
              id='streak-reminder-hour-help'
            >
              Escolha uma hora cheia entre 06:00 e 22:00, no seu fuso horário. A escolha
              vale para todos os seus navegadores.
            </p>
          </div>
        </div>
      )}
    </section>
  )
}
