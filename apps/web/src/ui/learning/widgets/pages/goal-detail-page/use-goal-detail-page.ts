import { useEffect, useState } from 'react'

import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import { useNavigation } from '@/ui/shared/hooks/use-navigation'

import { useGoalDetailQuery } from './use-goal-detail-query'

export type GoalDetailPageProps = { goalId: string }
export type GoalDetailView = 'graph' | 'list'
export type GoalDetailState = 'loading' | 'success' | 'empty' | 'not-found' | 'error'

export function useGoalDetailPage({ goalId }: GoalDetailPageProps) {
  const [view, setView] = useState<GoalDetailView>('graph')
  const { navigateTo } = useNavigation()
  const {
    goalDetail,
    goalDetailError,
    isFetchingGoalDetail,
    isLoadingGoalDetail,
    refetchGoalDetail,
  } = useGoalDetailQuery(goalId)
  const isSessionRejected = goalDetailError instanceof AuthError
  const isPrivateAbsence =
    goalDetailError instanceof RestError && goalDetailError.statusCode === 404
  const state: GoalDetailState = isLoadingGoalDetail
    ? 'loading'
    : isPrivateAbsence
      ? 'not-found'
      : goalDetailError || !goalDetail
        ? 'error'
        : goalDetail.skills.length === 0
          ? 'empty'
          : 'success'

  useEffect(() => {
    if (isSessionRejected) void navigateTo('login')
  }, [isSessionRejected, navigateTo])

  function handleViewChange(value: string) {
    if (value === 'graph' || value === 'list') setView(value)
  }

  function handleRetry() {
    void refetchGoalDetail()
  }

  return {
    detail: state === 'success' || state === 'empty' ? goalDetail : null,
    state,
    view,
    isRetrying: isFetchingGoalDetail && !isLoadingGoalDetail,
    handleViewChange,
    handleRetry,
  }
}

export type GoalDetailPageController = ReturnType<typeof useGoalDetailPage>
