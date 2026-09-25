import type { PropsWithChildren, ReactNode } from 'react'

import { AccountMenu, type LayoutAccount } from './account-menu'
import { DesktopHeader } from './desktop-header'
import { MobileBottomNavigation } from './mobile-bottom-navigation'
import { MobileHeader } from './mobile-header'
import { useAppLayout } from './use-app-layout'

export type AppLayoutProps = PropsWithChildren<{
  account?: LayoutAccount
  accountMenu?: ReactNode
}>

export const AppLayout = ({ account, accountMenu, children }: AppLayoutProps) => {
  const { navigationItems, pathname } = useAppLayout()
  const renderedAccountMenu =
    accountMenu ?? (account ? <AccountMenu account={account} /> : undefined)

  return (
    <div className='relative isolate min-h-screen bg-background text-foreground'>
      <header className='relative z-20 border-b border-border bg-background/80'>
        <DesktopHeader
          accountMenu={renderedAccountMenu}
          items={navigationItems}
          pathname={pathname}
        />
        <MobileHeader
          accountMenu={renderedAccountMenu}
          items={navigationItems}
          pathname={pathname}
        />
      </header>

      <main className='relative z-10 mx-auto flex min-h-[calc(100vh-4rem)] w-full max-w-7xl flex-1 flex-col px-5 py-8 pb-24 sm:px-8 lg:px-10 lg:pb-8'>
        {children}
      </main>
      <MobileBottomNavigation items={navigationItems} pathname={pathname} />
    </div>
  )
}
