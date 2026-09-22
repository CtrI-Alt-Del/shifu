export const ROUTES = {
  root: '/',
  dashboard: '/',
  login: '/login',
  register: '/register',
  forgotPassword: '/forgot-password',
  pendingConfirmation: '/pending-confirmation',
  curriculum: '/curriculum',
  learning: '/learning',
  learningGoalsNew: '/learning/goals/new',
  gamification: '/gamification',
  intelligence: '/intelligence',
  account: '/account',
} as const

export type RouteName = keyof typeof ROUTES
export type RoutePath = (typeof ROUTES)[RouteName]
