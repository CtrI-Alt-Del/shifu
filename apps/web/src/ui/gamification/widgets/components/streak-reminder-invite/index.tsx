import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/ui/shadcn/dialog'
import { Icon } from '@/ui/shared/widgets/components/icon'

import { HourStep } from './hour-step'
import { InviteStep } from './invite-step'
import { useStreakReminderInvite } from './use-streak-reminder-invite'

export type StreakReminderInviteProps = { accountEmail: string }

const STEP_COPY = {
  invite: {
    title: 'Quer um lembrete para manter sua sequência?',
    description:
      'Você praticou hoje e começou uma sequência. Se quiser, o Shifu avisa no horário que você escolher quando você ainda não tiver praticado no dia.',
  },
  hour: {
    title: 'Lembretes ativados',
    description:
      'Escolha o horário em que prefere ser lembrado. O lembrete só chega se você ainda não tiver praticado no dia.',
  },
} as const

export const StreakReminderInvite = (props: StreakReminderInviteProps) => {
  const {
    isOpen,
    step,
    hour,
    isEnabling,
    isSavingHour,
    selectPortalContainer,
    setSelectPortalContainer,
    handleHourChange,
    handleDecline,
    handleEnable,
    handleSaveHour,
    handleSkip,
    handleOpenChange,
    handleOpenAutoFocus,
    handleCloseAutoFocus,
  } = useStreakReminderInvite(props)
  const copy = STEP_COPY[step]

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogContent
        className='w-[calc(100%-2.5rem)]! max-w-120! rounded-[14px]! focus-visible:outline-none'
        onCloseAutoFocus={handleCloseAutoFocus}
        onOpenAutoFocus={handleOpenAutoFocus}
      >
        <DialogClose
          aria-label='Fechar'
          className='absolute right-4 top-4 inline-flex size-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-white/5 hover:text-foreground'
          type='button'
        >
          <Icon className='size-4' name='x' />
        </DialogClose>
        <DialogHeader className='mb-4! border-b border-border pb-4 text-left!'>
          <div className='flex items-start gap-3 pr-10'>
            <div className='flex size-11 shrink-0 items-center justify-center rounded-full bg-accent'>
              <Icon className='size-5 text-selo-text' name='flame' />
            </div>
            <div className='flex min-w-0 flex-col gap-1'>
              <DialogTitle className='text-lg font-semibold leading-snug text-foreground'>
                {copy.title}
              </DialogTitle>
              <DialogDescription className='text-[15px] leading-snug text-secondary-foreground'>
                {copy.description}
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>
        <div className='relative' ref={setSelectPortalContainer}>
          {step === 'invite' ? (
            <InviteStep
              isEnabling={isEnabling}
              onDecline={handleDecline}
              onEnable={handleEnable}
            />
          ) : (
            <HourStep
              hour={hour}
              isSavingHour={isSavingHour}
              onHourChange={handleHourChange}
              onSave={handleSaveHour}
              onSkip={handleSkip}
              selectPortalContainer={selectPortalContainer}
            />
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
