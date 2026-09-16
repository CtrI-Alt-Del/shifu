import type { PropsWithChildren, ReactNode } from 'react'

import { DesktopHeader } from './desktop-header'
import { MobileHeader } from './mobile-header'
import { useAppLayout } from './use-app-layout'
import { SquareBackground } from './square-background'

export type AppLayoutProps = PropsWithChildren<{
  accountMenu?: ReactNode
}>

export const AppLayout = ({ accountMenu, children }: AppLayoutProps) => {
  const { navigationItems, pathname } = useAppLayout()

  return (
    <div className='relative isolate min-h-screen bg-background text-foreground'>
      <SquareBackground />

      <header className='relative z-10 border-b border-border bg-background/80'>
        <DesktopHeader
          accountMenu={accountMenu}
          items={navigationItems}
          pathname={pathname}
        />
        <MobileHeader items={navigationItems} pathname={pathname} />
      </header>

      <main className='relative z-10 mx-auto flex min-h-[calc(100vh-4rem)] w-full max-w-6xl flex-1 flex-col px-5 py-8 sm:px-8 lg:px-10'>
        {children}
      </main>
    </div>
  )
}
