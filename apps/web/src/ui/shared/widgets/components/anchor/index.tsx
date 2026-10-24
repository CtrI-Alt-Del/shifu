import { Link } from '@tanstack/react-router'
import type { ComponentProps } from 'react'

import { ROUTES, type RouteName } from '@/constants/routes'

export type AnchorSearch = Record<string, string | number | boolean | undefined>

export type AnchorProps = Omit<ComponentProps<typeof Link>, 'to' | 'search'> & {
  route: RouteName
  /** Search values for the destination route; the route's validateSearch owns parsing. */
  search?: AnchorSearch
}

export const Anchor = ({ route, search, ...props }: AnchorProps) => {
  return <Link search={search as never} to={ROUTES[route] as never} {...props} />
}
