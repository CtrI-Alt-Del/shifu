export const ROUTES = {
  root: '/',
  dashboard: '/',
  curriculum: '/curriculum',
  learning: '/learning',
  gamification: '/gamification',
  intelligence: '/intelligence',
  account: '/account',
} as const

export type RouteName = keyof typeof ROUTES
export type RoutePath = (typeof ROUTES)[RouteName]
