import { GoalDetailFeedback } from './goal-detail-feedback'
import { GoalAddSkillLink, GoalDetailHeader } from './goal-detail-header'
import { GoalSkillGraph } from './goal-skill-graph'
import { GoalSkillList } from './goal-skill-list'
import { GoalViewSwitcher } from './goal-view-switcher'
import { type GoalDetailPageProps, useGoalDetailPage } from './use-goal-detail-page'

export type { GoalDetailPageProps } from './use-goal-detail-page'

export const GoalDetailPage = (props: GoalDetailPageProps) => {
  const {
    detail,
    state,
    view,
    isRetrying,
    isConfirmDialogOpen,
    isDeletingGoal,
    deleteGoalError,
    handleRetry,
    handleViewChange,
    handleOpenConfirmDialog,
    handleCancelRemoval,
    handleConfirmRemoval,
  } = useGoalDetailPage(props)

  if (state === 'loading') return <GoalDetailFeedback state='loading' />
  if (state === 'not-found') return <GoalDetailFeedback state='not-found' />
  if (state === 'error')
    return (
      <GoalDetailFeedback isRetrying={isRetrying} onRetry={handleRetry} state='error' />
    )
  if (!detail) return null

  return (
    <div className='mx-auto w-full max-w-7xl space-y-7 pb-6'>
      <GoalDetailHeader
        description={detail.description}
        title={detail.title}
        isConfirmDialogOpen={isConfirmDialogOpen}
        isDeletingGoal={isDeletingGoal}
        deleteGoalError={deleteGoalError}
        onOpenConfirmDialog={handleOpenConfirmDialog}
        onCancelRemoval={handleCancelRemoval}
        onConfirmRemoval={handleConfirmRemoval}
      />
      <div className='flex flex-wrap items-center justify-between gap-4'>
        <GoalViewSwitcher onViewChange={handleViewChange} view={view} />
        <GoalAddSkillLink goalId={props.goalId} />
      </div>
      {state === 'empty' ? (
        <GoalDetailFeedback goalId={props.goalId} state='empty' />
      ) : view === 'graph' ? (
        <GoalSkillGraph
          goalId={props.goalId}
          relations={detail.relations}
          skills={detail.skills}
          title={detail.title}
        />
      ) : (
        <GoalSkillList goalId={props.goalId} skills={detail.skills} />
      )}
    </div>
  )
}
