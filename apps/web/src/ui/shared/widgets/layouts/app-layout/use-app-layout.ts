import { useLocation } from '@tanstack/react-router'

import { ROUTES, type RouteName } from '@/constants/routes'
import type { IconName } from '@/ui/shared/widgets/components/icon'

type SidebarItem = {
  icon: IconName
  label: string
  route: RouteName
}

const SIDEBAR_ITEMS: readonly SidebarItem[] = [
  { icon: 'home', label: 'Visão geral', route: 'root' },
  { icon: 'book-open', label: 'Currículo', route: 'curriculum' },
  { icon: 'graduation-cap', label: 'Aprendizado', route: 'learning' },
  { icon: 'trophy', label: 'Gamificação', route: 'gamification' },
  { icon: 'sparkles', label: 'Inteligência', route: 'intelligence' },
]

const SIDEBAR_SECONDARY_ITEMS: readonly SidebarItem[] = [
  { icon: 'user-circle', label: 'Identidade', route: 'account' },
]

export function isSidebarItemActive(pathname: string, route: RouteName): boolean {
  const normalizedPathname = normalizePathname(pathname)
  const normalizedRoute = normalizePathname(ROUTES[route])

  return normalizedPathname === normalizedRoute
}

function normalizePathname(pathname: string): string {
  const normalized = pathname.replace(/\/+$/, '')
  return normalized || ROUTES.root
}

export function useAppLayout() {
  const location = useLocation()

  return {
    pathname: location.pathname,
    primaryItems: SIDEBAR_ITEMS,
    secondaryItems: SIDEBAR_SECONDARY_ITEMS,
  }
}
