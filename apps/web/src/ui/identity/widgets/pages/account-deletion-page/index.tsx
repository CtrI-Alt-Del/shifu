import { motion } from 'motion/react'
import { ENTRANCE_SECTION } from '@/constants/motion-variants'
import type { AccountErasureResult } from '@/rest/services/identity-service'
import { MotionEntrance } from '@/ui/shared/widgets/components/motion-entrance'
import { DeletionPanel } from './deletion-panel'

export const AccountDeletionPage = () => {
  return (
    <MotionEntrance>
      <motion.div variants={ENTRANCE_SECTION}>
        <DeletionPanel />
      </motion.div>
    </MotionEntrance>
  )
}

export const AccountDeletionStatusPage = ({
  status,
}: {
  status: AccountErasureResult
}) => {
  const isComplete = status.erasure === 'completed'

  return (
    <section
      aria-labelledby='account-deletion-page-title'
      className='mx-auto w-full max-w-3xl space-y-4 px-4 py-8 sm:px-6'
    >
      <h1 id='account-deletion-page-title' className='font-serif text-3xl'>
        Conta encerrada
      </h1>
      <section
        aria-labelledby='account-deletion-status-title'
        className='space-y-3 rounded-lg border border-border bg-card p-6'
      >
        <h2 id='account-deletion-status-title' className='text-base font-semibold'>
          {isComplete ? 'Eliminação concluída' : 'Eliminação em andamento'}
        </h2>
        <p className='text-sm leading-6 text-muted-foreground'>
          {isComplete
            ? 'O acesso à conta foi bloqueado e a eliminação dos dados ativos foi confirmada.'
            : 'O acesso à conta foi bloqueado. Os dados ativos sob controle do Shifu estão sendo eliminados em até 24 horas.'}
        </p>
        <p className='text-sm leading-6 text-muted-foreground'>
          Dados guardados em um navegador que ficou desconectado só podem ser removidos
          quando ele voltar a se comunicar com o Shifu.
        </p>
      </section>
    </section>
  )
}
