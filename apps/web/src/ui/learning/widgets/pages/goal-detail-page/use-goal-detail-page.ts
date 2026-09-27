import { useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import type { GoalSkillDetail } from '@/core/learning/goal-detail'
import { useRemoveSkillAction } from '@/ui/learning/hooks/use-remove-skill-action'
import { useNavigation } from '@/ui/shared/hooks/use-navigation'

import { useDeleteGoalAction } from './use-delete-goal-action'
import { useGoalDetailQuery } from './use-goal-detail-query'

export type GoalDetailPageProps = { goalId: string }
export type GoalDetailView = 'graph' | 'list'
export type GoalDetailState = 'loading' | 'success' | 'empty' | 'not-found' | 'error'

export function useGoalDetailPage({ goalId }: GoalDetailPageProps) {
  const [view, setView] = useState<GoalDetailView>('graph')
  const [isConfirmDialogOpen, setIsConfirmDialogOpen] = useState(false)
  const [selectedSkill, setSelectedSkill] = useState<GoalSkillDetail | null>(null)
  const skillRemovalTriggerRef = useRef<HTMLElement | null>(null)
  const isSkillRemovalSubmittingRef = useRef(false)
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
  const { isRemovingSkill, removeSkill, removeSkillError, resetRemoveSkill } =
    useRemoveSkillAction({ goalId, skillId: selectedSkill?.skillId ?? '' })
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

  function handleOpenSkillRemoval(skill: GoalSkillDetail, trigger?: HTMLButtonElement) {
    if (trigger) skillRemovalTriggerRef.current = trigger
    resetRemoveSkill()
    setSelectedSkill(skill)
  }

  function handleCancelSkillRemoval() {
    if (isRemovingSkill) return
    setSelectedSkill(null)
    resetRemoveSkill()
  }

  async function handleConfirmSkillRemoval() {
    if (!selectedSkill || isRemovingSkill || isSkillRemovalSubmittingRef.current) return
    isSkillRemovalSubmittingRef.current = true
    try {
      await removeSkill()
      await queryClient.invalidateQueries({
        queryKey: ['learning', 'goal-detail', goalId],
      })
      setSelectedSkill(null)
    } catch {
      // Mutation state owns the recoverable user-facing error.
    } finally {
      isSkillRemovalSubmittingRef.current = false
    }
  }

  return {
    detail: state === 'success' || state === 'empty' ? goalDetail : null,
    state,
    view,
    isRetrying: isFetchingGoalDetail && !isLoadingGoalDetail,
    isConfirmDialogOpen,
    isDeletingGoal,
    deleteGoalError,
    selectedSkill,
    isRemovingSkill,
    removeSkillError,
    skillRemovalTriggerRef,
    handleViewChange,
    handleRetry,
    handleOpenConfirmDialog,
    handleCancelRemoval,
    handleConfirmRemoval,
    handleOpenSkillRemoval,
    handleCancelSkillRemoval,
    handleConfirmSkillRemoval,
  }
}

export type GoalDetailPageController = ReturnType<typeof useGoalDetailPage>
