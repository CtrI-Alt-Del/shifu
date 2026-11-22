import { STREAK_REMINDER_HOUR_OPTIONS } from '@/ui/gamification/constants/streak-reminder-hour-options'
import { Button } from '@/ui/shadcn/button'
import { DialogFooter } from '@/ui/shadcn/dialog'
import { Label } from '@/ui/shadcn/label'
import { Select } from '@/ui/shadcn/select'

export type HourStepProps = {
  hour: number
  isSavingHour: boolean
  selectPortalContainer: HTMLElement | null
  onHourChange: (value: string | null) => void
  onSave: () => void
  onSkip: () => void
}

export const HourStep = ({
  hour,
  isSavingHour,
  selectPortalContainer,
  onHourChange,
  onSave,
  onSkip,
}: HourStepProps) => (
  <>
    <div className='space-y-2'>
      <Label className='block' htmlFor='streak-reminder-invite-hour'>
        Horário do lembrete
      </Label>
      <Select
        aria-describedby='streak-reminder-invite-hour-help'
        className='min-h-[52px]'
        disabled={isSavingHour}
        id='streak-reminder-invite-hour'
        onValueChange={onHourChange}
        options={STREAK_REMINDER_HOUR_OPTIONS}
        portalContainer={selectPortalContainer}
        value={String(hour)}
      />
      <p
        className='text-xs leading-5 text-muted-foreground'
        id='streak-reminder-invite-hour-help'
      >
        Hora cheia entre 06:00 e 22:00. Você pode mudar depois em Sua conta.
      </p>
    </div>
    <DialogFooter className='mt-6! flex-row! flex-wrap justify-end gap-3 border-t-0! pt-0! sm:space-x-0!'>
      <Button
        className='text-sm'
        disabled={isSavingHour}
        onClick={onSkip}
        type='button'
        variant='outline'
      >
        Pular
      </Button>
      <Button className='text-sm' disabled={isSavingHour} onClick={onSave} type='button'>
        {isSavingHour ? 'Salvando…' : 'Salvar horário'}
      </Button>
    </DialogFooter>
  </>
)
