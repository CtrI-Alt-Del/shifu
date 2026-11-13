import type { PropsWithChildren } from 'react'

import { AccountNavigation } from './account-navigation'

export type AccountLayoutProps = PropsWithChildren

export const AccountLayout = ({ children }: AccountLayoutProps) => {
  return (
    <div className='mx-auto w-full max-w-7xl'>
      <div className='mx-auto w-full max-w-[1150px] space-y-6'>
        <h1 className='font-serif text-4xl'>Sua conta</h1>
        <div>
          <AccountNavigation />
          <div className='mt-5 sm:mt-6'>{children}</div>
        </div>
      </div>
    </div>
  )
}
