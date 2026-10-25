import type { PropsWithChildren } from 'react'

import { GamificationNavigation } from './gamification-navigation'

export type GamificationLayoutProps = PropsWithChildren

export const GamificationLayout = ({ children }: GamificationLayoutProps) => {
  return (
    <div className='mx-auto w-full max-w-7xl space-y-10'>
      <header className='space-y-2'>
        <h1 className='font-serif text-4xl'>Gamificação</h1>
        <p className='text-muted-foreground'>
          Sua constância, seus marcos e o XP que você conquistou.
        </p>
      </header>

      <div>
        <GamificationNavigation />
        <div className='pt-8'>{children}</div>
      </div>
    </div>
  )
}
