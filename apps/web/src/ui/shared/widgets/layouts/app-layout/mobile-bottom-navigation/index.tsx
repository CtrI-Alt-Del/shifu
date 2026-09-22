import { Anchor } from '@/ui/shared/widgets/components/anchor'
import { Icon, type IconName } from '@/ui/shared/widgets/components/icon'

import { isNavigationItemActive, type NavigationItem } from '../use-app-layout'

type BottomNavigationRoute = 'root' | 'gamification' | 'intelligence' | 'account'

const NAVIGATION_ICONS: Record<BottomNavigationRoute, IconName> = {
  account: 'user-circle',
  root: 'home',
  gamification: 'trophy',
  intelligence: 'sparkles',
}

type MobileBottomNavigationProps = {
  items: readonly NavigationItem[]
  pathname: string
}

export const MobileBottomNavigation = ({
  items,
  pathname,
}: MobileBottomNavigationProps) => {
  const bottomItems: readonly NavigationItem[] = [
    ...items,
    { label: 'Conta', route: 'account' },
  ]

  return (
    <nav
      aria-label='Navegação inferior'
      className='fixed inset-x-0 bottom-0 z-20 border-t border-border bg-background/95 px-4 pb-[env(safe-area-inset-bottom)] pt-2 backdrop-blur lg:hidden'
    >
      <div className='mx-auto flex max-w-md items-center justify-around gap-2'>
        {bottomItems.map((item) => {
          const isActive = isNavigationItemActive(pathname, item.route)

          return (
            <Anchor
              aria-current={isActive ? 'page' : undefined}
              aria-label={`${item.label} — navegação inferior`}
              className={`flex min-h-11 min-w-16 flex-1 flex-col items-center justify-center gap-1 rounded-md px-2 py-1 text-xs font-medium transition-colors focus-visible:outline-offset-2 ${
                isActive
                  ? 'bg-white/5 text-foreground'
                  : 'text-muted-foreground hover:bg-white/5 hover:text-foreground'
              }`}
              key={item.route}
              route={item.route}
            >
              <Icon
                name={NAVIGATION_ICONS[item.route as BottomNavigationRoute]}
                size={18}
              />
              <span>{item.label}</span>
            </Anchor>
          )
        })}
      </div>
    </nav>
  )
}
