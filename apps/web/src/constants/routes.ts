export const ROUTES = {
  root: '/',
  dashboard: '/',
  login: '/login',
  register: '/register',
  forgotPassword: '/forgot-password',
  pendingConfirmation: '/pending-confirmation',
  confirmEmail: '/confirm-email',
  curriculum: '/curriculum',
  learning: '/learning',
  learningGoalsNew: '/learning/goals/new',
  learningGoalSkillsAdd: '/learning/goals/$goalId/skills/add',
  gamification: '/gamification',
  intelligence: '/intelligence',
  account: '/account',
  learningActivity:
    '/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId',
  learningAttempt:
    '/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId/attempts/$attemptId',
} as const

type StaticRouteName = Exclude<
  keyof typeof ROUTES,
  'learningActivity' | 'learningAttempt'
>

type LearningActivityRouteIds = {
  goalId: string
  skillId: string
  competencyId: string
  activityId: string
}

export function learningActivityPath({
  goalId,
  skillId,
  competencyId,
  activityId,
}: LearningActivityRouteIds) {
  return ROUTES.learningActivity
    .replace('$goalId', encodeURIComponent(goalId))
    .replace('$skillId', encodeURIComponent(skillId))
    .replace('$competencyId', encodeURIComponent(competencyId))
    .replace('$activityId', encodeURIComponent(activityId))
}

export function learningAttemptPath(
  ids: LearningActivityRouteIds & { attemptId: string },
) {
  return ROUTES.learningAttempt
    .replace('$goalId', encodeURIComponent(ids.goalId))
    .replace('$skillId', encodeURIComponent(ids.skillId))
    .replace('$competencyId', encodeURIComponent(ids.competencyId))
    .replace('$activityId', encodeURIComponent(ids.activityId))
    .replace('$attemptId', encodeURIComponent(ids.attemptId))
}

export function learningAttemptsPath(ids: LearningActivityRouteIds) {
  return `${learningActivityPath(ids)}/attempts`
}

export type RouteName = StaticRouteName
export type RoutePath = (typeof ROUTES)[RouteName]
