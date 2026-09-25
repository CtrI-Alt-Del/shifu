import { useNavigate } from '@tanstack/react-router'

import {
  ROUTES,
  learningActivityPath,
  learningAttemptPath,
  type RouteName,
} from '@/constants/routes'

type LearningActivityRouteIds = {
  goalId: string
  skillId: string
  competencyId: string
  activityId: string
}

type LearningAttemptRouteIds = LearningActivityRouteIds & {
  attemptId: string
}

type NavigationArgs =
  | [route: RouteName]
  | [route: 'learningActivity', ids: LearningActivityRouteIds]
  | [
      route: 'learningAttempt',
      ids: LearningAttemptRouteIds,
      options?: { replace?: boolean },
    ]

export function useNavigation() {
  const navigate = useNavigate()

  function navigateTo(...args: NavigationArgs) {
    const [route, ids, options] = args

    if (route === 'learningActivity') {
      return navigate({ to: learningActivityPath(ids) as never })
    }

    if (route === 'learningAttempt') {
      return navigate({
        to: learningAttemptPath(ids) as never,
        replace: options?.replace,
      })
    }

    return navigate({ to: ROUTES[route] as never })
  }

  return {
    navigateTo,
    navigateToGoalDetail(goalId: string) {
      return navigate({ params: { goalId }, to: '/learning/goals/$goalId' })
    },
    navigateToPlanner(planningId: string) {
      return navigate({ params: { planningId }, to: '/intelligence/planner/$planningId' })
    },
  }
}
