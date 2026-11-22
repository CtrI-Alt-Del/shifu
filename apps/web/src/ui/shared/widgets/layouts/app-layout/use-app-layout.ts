import { useLocation } from '@tanstack/react-router'

import { ROUTES, type RouteName } from '@/constants/routes'

export type NavigationItem = {
  label: string
  route: RouteName
  activeRoutes?: readonly RouteName[]
}

export const APP_NAVIGATION_ITEMS: readonly NavigationItem[] = [
  { label: 'Objetivos', route: 'root', activeRoutes: ['learning'] },
  { label: 'Progresso', route: 'gamification' },
  { label: 'Mentor', route: 'intelligence' },
]

export function isNavigationItemActive(pathname: string, item: NavigationItem): boolean {
  const normalizedPathname = normalizePathname(pathname)

  if (matchesRoute(normalizedPathname, item.route)) return true

  return (item.activeRoutes ?? []).some((route) =>
    matchesRoute(normalizedPathname, route),
  )
}

function matchesRoute(normalizedPathname: string, route: RouteName): boolean {
  const normalizedRoute = normalizePathname(ROUTES[route])

  if (route === 'root') return normalizedPathname === normalizedRoute

  return (
    normalizedPathname === normalizedRoute ||
    normalizedPathname.startsWith(`${normalizedRoute}/`)
  )
}

function normalizePathname(pathname: string): string {
  const normalized = pathname.replace(/\/+$/, '')
  return normalized || ROUTES.root
}

export function useAppLayout() {
  const location = useLocation()

  return {
    navigationItems: APP_NAVIGATION_ITEMS,
    pathname: location.pathname,
  }
}
