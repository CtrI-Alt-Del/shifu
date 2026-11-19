import type { ReactNode } from 'react'

import { AiQuotaIndicator } from '@/ui/intelligence/widgets/components/ai-quota-indicator'
import { Anchor } from '@/ui/shared/widgets/components/anchor'
import { Icon } from '@/ui/shared/widgets/components/icon'
import { Navigation, type NavigationProps } from '../navigation'

export type DesktopHeaderProps = NavigationProps & {
  accountMenu?: ReactNode
}

export const DesktopHeader = ({ accountMenu, items, pathname }: DesktopHeaderProps) => {
  return (
    <div className='mx-auto hidden h-16 w-full max-w-[1440px] items-center justify-between gap-8 px-5 sm:px-8 lg:flex'>
      <div className='flex min-w-0 items-center gap-8'>
        <Anchor
          aria-label='Shifu — Objetivos'
          className='flex shrink-0 items-center gap-1.5 rounded-md focus-visible:outline-offset-4'
          route='root'
        >
          <span className='font-serif text-[26px] leading-none text-foreground'>
            Shifu
          </span>
          <span className='font-serif text-base leading-none text-selo-text'>師</span>
        </Anchor>
        <nav aria-label='Navegação principal' className='flex items-center gap-1'>
          <Navigation items={items} pathname={pathname} />
        </nav>
      </div>
      <div className='flex shrink-0 items-center gap-2'>
        <AiQuotaIndicator />
        {accountMenu ?? (
          <button
            aria-label='Abrir menu da conta'
            className='grid size-11 shrink-0 place-items-center rounded-full text-muted-foreground transition-colors hover:text-foreground'
            data-account-menu-trigger
            type='button'
          >
            <span className='grid size-8 place-items-center rounded-full border border-white/10 bg-muted'>
              <Icon name='user-round' size={16} />
            </span>
          </button>
        )}
      </div>
    </div>
  )
}
