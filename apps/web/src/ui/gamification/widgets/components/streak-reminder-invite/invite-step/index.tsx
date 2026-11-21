import { Button } from '@/ui/shadcn/button'
import { DialogFooter } from '@/ui/shadcn/dialog'

export type InviteStepProps = {
  isEnabling: boolean
  onDecline: () => void
  onEnable: () => void
}

export const InviteStep = ({ isEnabling, onDecline, onEnable }: InviteStepProps) => (
  <>
    <p className='text-[13px] leading-5 text-muted-foreground'>
      O navegador vai pedir sua permissão. Você pode mudar isso depois em Sua conta.
    </p>
    <DialogFooter className='mt-6! flex-row! flex-wrap justify-end gap-3 border-t-0! pt-0! sm:space-x-0!'>
      <Button
        className='text-sm'
        disabled={isEnabling}
        onClick={onDecline}
        type='button'
        variant='outline'
      >
        Agora não
      </Button>
      <Button
        className='text-sm'
        disabled={isEnabling}
        id='streak-reminder-invite-enable'
        onClick={onEnable}
        type='button'
      >
        {isEnabling ? 'Ativando…' : 'Ativar lembretes'}
      </Button>
    </DialogFooter>
  </>
)
