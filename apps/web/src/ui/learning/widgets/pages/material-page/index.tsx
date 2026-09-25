import { MaterialContent } from './material-content'
import { MaterialFeedback } from './material-feedback'
import { MaterialHeader } from './material-header'
import { MaterialRecommendation } from './material-recommendation'
import { type MaterialPageProps, useMaterialPage } from './use-material-page'

export type { MaterialPageProps } from './use-material-page'

export const MaterialPage = (props: MaterialPageProps) => {
  const {
    detail,
    handleOpenRecommendation,
    handleRetry,
    hasActivityFailure,
    isLoading,
    isOpeningActivity,
    isPrivateAbsence,
    isRecoverableError,
  } = useMaterialPage(props)

  if (isLoading) {
    return <MaterialFeedback state='loading' />
  }

  if (isPrivateAbsence) {
    return <MaterialFeedback state='private-absence' />
  }

  if (isRecoverableError || !detail) {
    return <MaterialFeedback onRetry={() => void handleRetry()} state='error' />
  }

  if (detail.availability === 'unavailable') {
    return (
      <MaterialFeedback
        competencyId={props.competencyId}
        competencyName={detail.competencyName}
        focusCompetencyId={detail.focusCompetencyId}
        focusCompetencyName={detail.focusCompetencyName}
        goalId={props.goalId}
        skillId={props.skillId}
        state='unavailable'
      />
    )
  }

  const { recommendation } = detail

  return (
    <article className='space-y-7 pb-6 sm:space-y-9'>
      <MaterialHeader
        competencyId={detail.competencyId}
        competencyName={detail.competencyName}
        goalId={detail.goalId}
        materialTitle={detail.materialTitle}
        skillId={detail.skillId}
        skillName={detail.skillName}
      />
      <MaterialContent content={detail.content} />
      <p className='text-sm text-muted-foreground'>
        A leitura é opcional e não altera seu progresso. Você pode praticar a qualquer
        momento.
      </p>
      {recommendation ? (
        <MaterialRecommendation
          competencyName={detail.competencyName}
          hasFailure={hasActivityFailure}
          isPending={isOpeningActivity}
          onOpen={() => void handleOpenRecommendation(recommendation.activityId)}
          recommendation={recommendation}
        />
      ) : null}
    </article>
  )
}
