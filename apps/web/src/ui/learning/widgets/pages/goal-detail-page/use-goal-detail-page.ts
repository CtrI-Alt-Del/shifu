import { useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import { useNavigation } from '@/ui/shared/hooks/use-navigation'

import { useDeleteGoalAction } from './use-delete-goal-action'
import { useGoalDetailQuery } from './use-goal-detail-query'

export type GoalDetailPageProps = { goalId: string }
export type GoalDetailView = 'graph' | 'list'
export type GoalDetailState = 'loading' | 'success' | 'empty' | 'not-found' | 'error'

export function useGoalDetailPage({ goalId }: GoalDetailPageProps) {
  const [view, setView] = useState<GoalDetailView>('graph')
  const [isConfirmDialogOpen, setIsConfirmDialogOpen] = useState(false)
  const { navigateTo } = useNavigation()
  const queryClient = useQueryClient()
  const {
    goalDetail,
    goalDetailError,
    isFetchingGoalDetail,
    isLoadingGoalDetail,
    refetchGoalDetail,
  } = useGoalDetailQuery(goalId)
  const { deleteGoal, isDeletingGoal, deleteGoalError } = useDeleteGoalAction(goalId)
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

  function handleOpenConfirmDialog() {
    setIsConfirmDialogOpen(true)
  }

  function handleCancelRemoval() {
    setIsConfirmDialogOpen(false)
  }

  function handleConfirmRemoval() {
    deleteGoal(undefined, {
      onSuccess: async () => {
        await queryClient.invalidateQueries({ queryKey: ['learning', 'home-goals'] })
        navigateTo('root')
      },
    })
  }

  return {
    detail: state === 'success' || state === 'empty' ? goalDetail : null,
    state,
    view,
    isRetrying: isFetchingGoalDetail && !isLoadingGoalDetail,
    isConfirmDialogOpen,
    isDeletingGoal,
    deleteGoalError,
    handleViewChange,
    handleRetry,
    handleOpenConfirmDialog,
    handleCancelRemoval,
    handleConfirmRemoval,
  }
}

export type GoalDetailPageController = ReturnType<typeof useGoalDetailPage>
