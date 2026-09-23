import { useCallback } from 'react'
import { createFileRoute } from '@tanstack/react-router'

import type { ActivityRecommendation } from '@/core/learning/competency-detail'
import { useNavigation } from '@/ui/shared/hooks/use-navigation'
import { ChoiceResultPage } from '@/ui/learning/widgets/pages/choice-result-page'

export const Route = createFileRoute(
  '/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId/attempts/$attemptId/',
)({ component: AttemptIndexRoute })

function AttemptIndexRoute() {
  const ids = Route.useParams()
  const { navigateTo } = useNavigation()
  const navigateToActivity = useCallback(
    () => navigateTo('learningActivity', ids),
    [ids, navigateTo],
  )
  const onSessionExpired = useCallback(() => navigateTo('login'), [navigateTo])
  const openRecommendation = useCallback(
    (recommendation: ActivityRecommendation) =>
      navigateTo('learningActivity', {
        goalId: ids.goalId,
        skillId: ids.skillId,
        competencyId: recommendation.competencyId,
        activityId: recommendation.activityId,
      }),
    [ids.goalId, ids.skillId, navigateTo],
  )

  return (
    <ChoiceResultPage
      {...ids}
      onNavigateToActivity={navigateToActivity}
      onOpenRecommendation={openRecommendation}
      onSessionExpired={onSessionExpired}
    />
  )
}
