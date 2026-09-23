import { useCallback, useRef } from 'react'
import { createFileRoute, useBlocker } from '@tanstack/react-router'

import { useNavigation } from '@/ui/shared/hooks/use-navigation'
import { ChoiceActivityPage } from '@/ui/learning/widgets/pages/choice-activity-page'

export const Route = createFileRoute(
  '/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId/',
)({ component: ActivityIndexRoute })

function ActivityIndexRoute() {
  const ids = Route.useParams()
  const { navigateTo } = useNavigation()
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
  const onUnsentAnswersChange = useCallback((hasUnsent: boolean) => {
    hasUnsentAnswersRef.current = hasUnsent
  }, [])

  return (
    <ChoiceActivityPage
      {...ids}
      onNavigateToAttempt={navigateToAttempt}
      onSessionExpired={onSessionExpired}
      onUnsentAnswersChange={onUnsentAnswersChange}
    />
  )
}
