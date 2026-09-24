import { useNavigate } from '@tanstack/react-router'

import { ROUTES, type RouteName } from '@/constants/routes'

export function useNavigation() {
  const navigate = useNavigate()

  return {
    navigateTo(route: RouteName) {
      return navigate({ to: ROUTES[route] as never })
    },
    navigateToGoalDetail(goalId: string) {
      return navigate({ params: { goalId }, to: '/learning/goals/$goalId' })
    },
    navigateToActivity(
      goalId: string,
      skillId: string,
      competencyId: string,
      activityId: string,
    ) {
      return navigate({
        params: { activityId, competencyId, goalId, skillId },
        to: '/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId',
      })
    },
    navigateToPlanner(planningId: string) {
      return navigate({ params: { planningId }, to: '/intelligence/planner/$planningId' })
    },
  }
}
