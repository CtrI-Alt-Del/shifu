import { useLocation } from '@tanstack/react-router'

import { ROUTES } from '@/constants/routes'

export const PUBLIC_ROUTE_PATHS = [
  ROUTES.login,
  ROUTES.register,
  ROUTES.forgotPassword,
  ROUTES.pendingConfirmation,
] as const

export function isPublicRoute(pathname: string): boolean {
  const normalizedPathname = pathname.replace(/\/+$/, '') || ROUTES.root

  return PUBLIC_ROUTE_PATHS.some((route) => {
    const normalizedRoute = route.replace(/\/+$/, '') || ROUTES.root
    return normalizedPathname === normalizedRoute
  })
}

export function useRootLayout() {
  const location = useLocation()

  return {
    isPublic: isPublicRoute(location.pathname),
  }
}
