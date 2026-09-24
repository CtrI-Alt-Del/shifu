import { CompetencyContentList } from './competency-content-list'
import { CompetencyDetailFeedback } from './competency-detail-feedback'
import { CompetencyDetailHeader } from './competency-detail-header'
import { AdaptiveRecommendation } from './adaptive-recommendation'
import {
  type CompetencyDetailPageProps,
  useCompetencyDetailPage,
} from './use-competency-detail-page'

export type { CompetencyDetailPageProps } from './use-competency-detail-page'

export const CompetencyDetailPage = (props: CompetencyDetailPageProps) => {
  const { detail, handleRetry, isLoading, isPrivateAbsence, isRecoverableError } =
    useCompetencyDetailPage(props)

  if (isLoading) {
    return <CompetencyDetailFeedback state='loading' />
  }

  if (isPrivateAbsence) {
    return <CompetencyDetailFeedback state='private-absence' />
  }

  if (isRecoverableError || !detail) {
    return <CompetencyDetailFeedback onRetry={() => void handleRetry()} state='error' />
  }

  if (detail.availability === 'unavailable') {
    return (
      <CompetencyDetailFeedback
        focusCompetencyName={detail.focusCompetencyName}
        goalId={props.goalId}
        skillId={props.skillId}
        state='unavailable'
      />
    )
  }

  return (
    <div className='mx-auto w-full max-w-7xl space-y-7 pb-6 sm:space-y-9'>
      <CompetencyDetailHeader
        detail={detail}
        goalId={props.goalId}
        skillId={props.skillId}
      />
      <AdaptiveRecommendation detail={detail} />
      <CompetencyContentList
        detail={detail}
        goalId={props.goalId}
        skillId={props.skillId}
      />
    </div>
  )
}
