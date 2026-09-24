import { GoalDetailFeedback } from './goal-detail-feedback'
import { GoalDetailHeader } from './goal-detail-header'
import { GoalSkillGraph } from './goal-skill-graph'
import { GoalSkillList } from './goal-skill-list'
import { GoalViewSwitcher } from './goal-view-switcher'
import { type GoalDetailPageProps, useGoalDetailPage } from './use-goal-detail-page'

export type { GoalDetailPageProps } from './use-goal-detail-page'

export const GoalDetailPage = (props: GoalDetailPageProps) => {
  const { detail, state, view, isRetrying, handleRetry, handleViewChange } =
    useGoalDetailPage(props)

  if (state === 'loading') return <GoalDetailFeedback state='loading' />
  if (state === 'not-found') return <GoalDetailFeedback state='not-found' />
  if (state === 'error')
    return (
      <GoalDetailFeedback isRetrying={isRetrying} onRetry={handleRetry} state='error' />
    )
  if (!detail) return null

  return (
    <div className='space-y-7 pb-6 sm:space-y-9'>
      <GoalDetailHeader
        description={detail.description}
        goalId={props.goalId}
        title={detail.title}
      />
      {state === 'empty' ? (
        <GoalDetailFeedback goalId={props.goalId} state='empty' />
      ) : (
        <>
          <GoalViewSwitcher onViewChange={handleViewChange} view={view} />
          {view === 'graph' ? (
            <GoalSkillGraph
              goalId={props.goalId}
              relations={detail.relations}
              skills={detail.skills}
            />
          ) : (
            <GoalSkillList goalId={props.goalId} skills={detail.skills} />
          )}
        </>
      )}
    </div>
  )
}
