import { useNavigate } from '@tanstack/react-router'

import { ROUTES, type RouteName } from '@/constants/routes'

export function useNavigation() {
  const navigate = useNavigate()

  return {
    navigateTo(route: RouteName) {
      return navigate({ to: ROUTES[route] as never })
    },
  }
}
