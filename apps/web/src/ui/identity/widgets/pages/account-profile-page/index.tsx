import { motion } from 'motion/react'
import { ENTRANCE_SECTION } from '@/constants/motion-variants'
import { Button } from '@/ui/shadcn/button'
import { MotionEntrance } from '@/ui/shared/widgets/components/motion-entrance'
import { PrivacyCard } from './privacy-card'
import { ProfileForm } from './profile-form'
import { useAccountProfilePage } from './use-account-profile-page'

export type AccountProfilePageProps = { accountEmail: string }

export const AccountProfilePage = (props: AccountProfilePageProps) => {
  const {
    accountProfile,
    isLoadingAccountProfile,
    accountProfileError,
    refetchAccountProfile,
  } = useAccountProfilePage(props)
  if (isLoadingAccountProfile) {
    return (
      <div
        aria-busy='true'
        className='animate-pulse space-y-5 rounded-lg border border-border bg-card p-6 motion-reduce:animate-none'
      >
        <output aria-label='Carregando sua conta' className='sr-only'>
          Carregando sua conta
        </output>
        <div className='h-5 w-40 rounded bg-muted' />
        <div className='h-12 rounded bg-muted' />
        <div className='h-12 rounded bg-muted' />
      </div>
    )
  }
  if (accountProfileError && !accountProfile) {
    return (
      <div role='alert' className='rounded-lg border border-border bg-card p-6'>
        <p>{accountProfileError.message}</p>
        <Button className='mt-4' onClick={refetchAccountProfile} variant='outline'>
          Tentar novamente
        </Button>
      </div>
    )
  }
  if (!accountProfile) return null
  return (
    <MotionEntrance>
      <motion.div variants={ENTRANCE_SECTION} className='space-y-5'>
        {accountProfileError && (
          <div role='alert' className='rounded-lg border border-border bg-card p-6'>
            <p>Não foi possível atualizar os dados da conta. Seu rascunho foi mantido.</p>
            <Button className='mt-4' variant='outline' onClick={refetchAccountProfile}>
              Tentar novamente
            </Button>
          </div>
        )}
        <ProfileForm profile={accountProfile} />
        <PrivacyCard />
      </motion.div>
    </MotionEntrance>
  )
}
