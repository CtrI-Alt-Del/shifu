import { Anchor } from '@/ui/shared/widgets/components/anchor'
import { isNavigationItemActive, type NavigationItem } from '../use-app-layout'

export type NavigationProps = {
  items: readonly NavigationItem[]
  pathname: string
  onNavigate?: () => void
}

export const Navigation = ({ items, pathname, onNavigate }: NavigationProps) => {
  return (
    <>
      {items.map((item) => {
        const isActive = isNavigationItemActive(pathname, item.route)

        return (
          <Anchor
            aria-current={isActive ? 'page' : undefined}
            className={`rounded-md px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-offset-2 ${
              isActive
                ? 'bg-muted text-foreground'
                : 'text-muted-foreground hover:bg-muted hover:text-foreground'
            }`}
            key={item.route}
            onClick={onNavigate}
            route={item.route}
          >
            {item.label}
          </Anchor>
        )
      })}
    </>
  )
}
