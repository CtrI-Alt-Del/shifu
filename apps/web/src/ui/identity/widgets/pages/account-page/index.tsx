import { Activity } from 'react'
import { motion } from 'motion/react'
import { ENTRANCE_SECTION } from '@/constants/motion-variants'
import { Button } from '@/ui/shadcn/button'
import { Tabs, TabsList, TabsTrigger } from '@/ui/shadcn/tabs'
import { MotionEntrance } from '@/ui/shared/widgets/components/motion-entrance'
import { ProfileForm } from './profile-form'
import { SecurityForm } from './security-form'
import { PrivacyCard } from './privacy-card'
import { useAccountPage } from './use-account-page'

export type AccountPageProps = { accountEmail: string }

export const AccountPage = (props: AccountPageProps) => {
  const {
    activeTab,
    accountProfile,
    isLoadingAccountProfile,
    accountProfileError,
    handleTabChange,
    refetchAccountProfile,
  } = useAccountPage(props)
  return (
    <div className='mx-auto w-full max-w-7xl'>
      <div className='mx-auto w-full max-w-[1150px] space-y-6'>
        <h1 className='font-serif text-4xl'>Sua conta</h1>
        {isLoadingAccountProfile ? (
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
        ) : accountProfileError && !accountProfile ? (
          <div role='alert' className='rounded-lg border border-border bg-card p-6'>
            <p>{accountProfileError.message}</p>
            <Button className='mt-4' onClick={refetchAccountProfile} variant='outline'>
              Tentar novamente
            </Button>
          </div>
        ) : (
          accountProfile && (
            <MotionEntrance>
              <motion.div variants={ENTRANCE_SECTION}>
                <Tabs value={activeTab} onValueChange={handleTabChange}>
                  {accountProfileError && (
                    <div
                      role='alert'
                      className='mb-5 rounded-lg border border-border bg-card p-6'
                    >
                      <p>
                        Não foi possível atualizar os dados da conta. Seu rascunho foi
                        mantido.
                      </p>
                      <Button
                        className='mt-4'
                        variant='outline'
                        onClick={refetchAccountProfile}
                      >
                        Tentar novamente
                      </Button>
                    </div>
                  )}
                  <TabsList aria-label='Configurações da conta'>
                    <TabsTrigger
                      value='profile'
                      id='account-tab-profile'
                      aria-controls='account-panel-profile'
                      className='min-h-11'
                    >
                      Perfil
                    </TabsTrigger>
                    <TabsTrigger
                      value='security'
                      id='account-tab-security'
                      aria-controls='account-panel-security'
                      className='min-h-11'
                    >
                      Segurança
                    </TabsTrigger>
                  </TabsList>
                  <div className='mt-5'>
                    <Activity mode={activeTab === 'profile' ? 'visible' : 'hidden'}>
                      <div
                        id='account-panel-profile'
                        role='tabpanel'
                        aria-labelledby='account-tab-profile'
                        className='space-y-5'
                      >
                        <ProfileForm profile={accountProfile} />
                        <PrivacyCard />
                      </div>
                    </Activity>
                    <Activity mode={activeTab === 'security' ? 'visible' : 'hidden'}>
                      <div
                        id='account-panel-security'
                        role='tabpanel'
                        aria-labelledby='account-tab-security'
                      >
                        <SecurityForm />
                      </div>
                    </Activity>
                  </div>
                </Tabs>
              </motion.div>
            </MotionEntrance>
          )
        )}
      </div>
    </div>
  )
}
