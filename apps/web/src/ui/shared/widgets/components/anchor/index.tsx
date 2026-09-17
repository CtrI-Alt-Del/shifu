import { Link } from '@tanstack/react-router'
import type { ComponentProps } from 'react'

import { ROUTES, type RouteName } from '@/constants/routes'

export type AnchorProps = Omit<ComponentProps<typeof Link>, 'to'> & {
  route: RouteName
}

export const Anchor = ({ route, ...props }: AnchorProps) => {
  return <Link to={ROUTES[route] as never} {...props} />
}
