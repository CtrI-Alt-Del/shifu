import { Anchor } from '@/ui/shared/widgets/components/anchor'
import { Icon } from '@/ui/shared/widgets/components/icon'
import { Navigation, type NavigationProps } from '../navigation'
import { useMobileHeader } from './use-mobile-header'

export type MobileHeaderProps = NavigationProps

export const MobileHeader = ({ items, pathname }: MobileHeaderProps) => {
  const { handleMenuToggle, handleNavigation, isMenuOpen, menuRef } = useMobileHeader()

  return (
    <div className='mx-auto flex h-15 w-full max-w-[1440px] items-center justify-between px-5 lg:hidden'>
      <Anchor
        aria-label='Shifu — Objetivos'
        className='flex items-center gap-1.5 rounded-md focus-visible:outline-offset-4'
        route='root'
      >
        <span className='font-serif text-2xl leading-none text-foreground'>Shifu</span>
        <span className='font-serif text-[15px] leading-none text-primary'>師</span>
      </Anchor>
      <div className='relative' ref={menuRef}>
        <button
          aria-controls='mobile-navigation'
          aria-expanded={isMenuOpen}
          aria-label={isMenuOpen ? 'Fechar menu' : 'Abrir menu'}
          className='grid size-9 place-items-center rounded-md bg-muted text-foreground transition-colors hover:bg-muted/80'
          onClick={handleMenuToggle}
          type='button'
        >
          <Icon name={isMenuOpen ? 'x' : 'menu'} />
        </button>
        {isMenuOpen && (
          <nav
            aria-label='Navegação móvel'
            className='absolute right-0 top-full z-20 mt-3 flex min-w-52 flex-col gap-1 rounded-lg border border-border bg-card p-2 shadow-card'
            id='mobile-navigation'
          >
            <Navigation items={items} onNavigate={handleNavigation} pathname={pathname} />
          </nav>
        )}
      </div>
    </div>
  )
}
