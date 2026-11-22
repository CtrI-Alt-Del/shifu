import type { StreakReminderCardNotice } from '../use-streak-reminder-card'

export type BlockedNoticeProps = {
  notice: NonNullable<StreakReminderCardNotice>
}

const NOTICE_COPY = {
  blocked: {
    title: 'Notificações bloqueadas neste navegador',
    description:
      'Para receber o lembrete aqui, permita notificações do Shifu nas configurações do navegador. Seus outros navegadores continuam recebendo normalmente.',
  },
  unsupported: {
    title: 'Este navegador não recebe notificações',
    description:
      'Para receber o lembrete, abra o Shifu em um navegador compatível. Sua escolha vale para todos os seus navegadores.',
  },
} as const

export const BlockedNotice = ({ notice }: BlockedNoticeProps) => (
  <output className='flex flex-col gap-1 rounded-md bg-latao-tint px-4 py-3'>
    <p className='text-sm font-semibold leading-tight text-latao-text'>
      {NOTICE_COPY[notice].title}
    </p>
    <p className='text-[13px] leading-[1.25] text-secondary-foreground'>
      {NOTICE_COPY[notice].description}
    </p>
  </output>
)
