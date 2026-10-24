export const ROUTES = {
  root: '/',
  dashboard: '/',
  login: '/login',
  register: '/register',
  privacy: '/privacy',
  forgotPassword: '/forgot-password',
  resetPassword: '/reset-password',
  pendingConfirmation: '/pending-confirmation',
  confirmEmail: '/confirm-email',
  curriculum: '/curriculum',
  learning: '/learning',
  learningGoalsNew: '/learning/goals/new',
  learningGoal: '/learning/goals/$goalId',
  learningSkill: '/learning/goals/$goalId/skills/$skillId',
  learningGoalSkillsAdd: '/learning/goals/$goalId/skills/add',
  gamification: '/gamification',
  intelligence: '/intelligence',
  intelligenceMemories: '/intelligence/memories',
  account: '/account',
  learningActivity:
    '/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId',
  learningAttempt:
    '/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId/attempts/$attemptId',
  learningDiagnosticResult: '/learning/goals/$goalId/skills/$skillId/diagnostic/result',
} as const

type StaticRouteName = Exclude<
  keyof typeof ROUTES,
  | 'learningGoal'
  | 'learningSkill'
  | 'learningActivity'
  | 'learningAttempt'
  | 'learningDiagnosticResult'
>

type LearningActivityRouteIds = {
  goalId: string
  skillId: string
  competencyId: string
  activityId: string
}

export function learningGoalPath({ goalId }: { goalId: string }) {
  return ROUTES.learningGoal.replace('$goalId', encodeURIComponent(goalId))
}

export function learningSkillPath({
  goalId,
  skillId,
}: {
  goalId: string
  skillId: string
}) {
  return ROUTES.learningSkill
    .replace('$goalId', encodeURIComponent(goalId))
    .replace('$skillId', encodeURIComponent(skillId))
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

export function learningDiagnosticResultPath({
  goalId,
  skillId,
}: {
  goalId: string
  skillId: string
}) {
  return ROUTES.learningDiagnosticResult
    .replace('$goalId', encodeURIComponent(goalId))
    .replace('$skillId', encodeURIComponent(skillId))
}

export type RouteName = StaticRouteName
export type RoutePath = (typeof ROUTES)[RouteName]

export function buildMentorResponseEventsPath(sessionId: string): string {
  return `/api/intelligence/mentor-sessions/${encodeURIComponent(sessionId)}/events`
}

export function buildMentorAttachmentUploadPath(batchId: string): string {
  return `/api/intelligence/mentor-attachment-batches/${encodeURIComponent(batchId)}/attachments`
}

export function buildMentorAttachmentFilePath(
  sessionId: string,
  attachmentId: string,
): string {
  return `/api/intelligence/mentor-sessions/${encodeURIComponent(sessionId)}/attachments/${encodeURIComponent(attachmentId)}/file`
}
