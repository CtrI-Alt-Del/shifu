import { useLocation } from '@tanstack/react-router'

import { ROUTES, type RouteName } from '@/constants/routes'

export type NavigationItem = {
  label: string
  route: RouteName
}

export const APP_NAVIGATION_ITEMS: readonly NavigationItem[] = [
  { label: 'Objetivos', route: 'root' },
  { label: 'Progresso', route: 'gamification' },
  { label: 'Mentor', route: 'intelligence' },
]

export function isNavigationItemActive(pathname: string, route: RouteName): boolean {
  const normalizedPathname = normalizePathname(pathname)
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
