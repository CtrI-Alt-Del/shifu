import { useCallback, useRef } from 'react'
import { createFileRoute, useBlocker, useNavigate } from '@tanstack/react-router'

import { requireAuthMiddleware } from '@/middlewares/require-auth-middleware'
import { useNavigation } from '@/ui/shared/hooks/use-navigation'
import { WebContainerCodePracticeRunner } from '@/provision/learning/webcontainer-code-practice-runner'
import { getDiagnosticRun } from '@/ui/learning/diagnostic-run-session'
import { useDiagnosticLeaveGuard } from '@/ui/learning/hooks/use-diagnostic-leave-guard'
import { ActivityPage } from '@/ui/learning/widgets/pages/activity-page'

export const Route = createFileRoute(
  '/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId/',
)({
  beforeLoad: () => requireAuthMiddleware(),
  component: ActivityIndexRoute,
})

function ActivityIndexRoute() {
  const ids = Route.useParams()
  const { navigateTo } = useNavigation()
  const navigate = useNavigate()
  const hasUnsentAnswersRef = useRef(false)
  const diagnosticRun = getDiagnosticRun(ids.goalId, ids.skillId)

  useDiagnosticLeaveGuard({
    goalId: ids.goalId,
    skillId: ids.skillId,
    diagnosticRunId: diagnosticRun?.diagnosticRunId ?? '',
    isActive: Boolean(diagnosticRun),
  })

  useBlocker({
    shouldBlockFn: () =>
      !diagnosticRun &&
      hasUnsentAnswersRef.current &&
      !window.confirm('Suas respostas não foram enviadas. Deseja sair desta Atividade?'),
    enableBeforeUnload: false,
  })

  const navigateToAttempt = useCallback(
    (attemptId: string, replace = false) =>
      navigateTo('learningAttempt', { ...ids, attemptId }, { replace }),
    [ids, navigateTo],
  )
  const onSessionExpired = useCallback(() => navigateTo('login'), [navigateTo])
  const navigateToDiagnostic = useCallback(
    () =>
      navigate({
        to: '/learning/goals/$goalId/skills/$skillId',
        params: { goalId: ids.goalId, skillId: ids.skillId },
        replace: true,
      }),
    [ids.goalId, ids.skillId, navigate],
  )
  const onNavigateToNextActivity = useCallback(
    (competencyId: string, activityId: string) =>
      navigate({
        to: '/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId',
        params: { goalId: ids.goalId, skillId: ids.skillId, competencyId, activityId },
        replace: true,
      }),
    [ids.goalId, ids.skillId, navigate],
  )
  const onNavigateToResult = useCallback(
    () =>
      navigate({
        to: '/learning/goals/$goalId/skills/$skillId/diagnostic/result',
        params: { goalId: ids.goalId, skillId: ids.skillId },
        replace: true,
      }),
    [ids.goalId, ids.skillId, navigate],
  )
  const onUnsentAnswersChange = useCallback((hasUnsent: boolean) => {
    hasUnsentAnswersRef.current = hasUnsent
  }, [])

  return (
    <ActivityPage
      {...ids}
      key={`${diagnosticRun?.diagnosticRunId ?? 'learning'}:${ids.activityId}`}
      diagnosticRunId={diagnosticRun?.diagnosticRunId}
      onNavigateToAttempt={navigateToAttempt}
      onNavigateToDiagnostic={navigateToDiagnostic}
      onNavigateToNextActivity={onNavigateToNextActivity}
      onNavigateToResult={onNavigateToResult}
      onSessionExpired={onSessionExpired}
      onUnsentAnswersChange={onUnsentAnswersChange}
      runnerFactory={WebContainerCodePracticeRunner}
    />
  )
}
