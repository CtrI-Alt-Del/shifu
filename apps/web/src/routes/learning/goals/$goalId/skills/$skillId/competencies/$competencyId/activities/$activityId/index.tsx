import { useCallback, useRef } from 'react'
import { createFileRoute, useBlocker, useNavigate } from '@tanstack/react-router'

import { useNavigation } from '@/ui/shared/hooks/use-navigation'
import { ChoiceActivityPage } from '@/ui/learning/widgets/pages/choice-activity-page'

export const Route = createFileRoute(
  '/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId/',
)({ component: ActivityIndexRoute })

function ActivityIndexRoute() {
  const ids = Route.useParams()
  const { navigateTo } = useNavigation()
  const navigate = useNavigate()
  const hasUnsentAnswersRef = useRef(false)

  useBlocker({
    shouldBlockFn: () =>
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
  const onUnsentAnswersChange = useCallback((hasUnsent: boolean) => {
    hasUnsentAnswersRef.current = hasUnsent
  }, [])

  return (
    <ChoiceActivityPage
      {...ids}
      onNavigateToAttempt={navigateToAttempt}
      onNavigateToDiagnostic={navigateToDiagnostic}
      onSessionExpired={onSessionExpired}
      onUnsentAnswersChange={onUnsentAnswersChange}
    />
  )
}
