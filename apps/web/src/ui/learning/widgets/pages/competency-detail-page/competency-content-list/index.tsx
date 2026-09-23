import type {
  AvailableCompetencyDetail,
  CompetencyDetailItem,
} from '@/core/learning/competency-detail'

import {
  CompetencyContentRow,
  type CompetencyContentRowProps,
} from './competency-content-row'

export type CompetencyContentListProps = {
  detail: AvailableCompetencyDetail
  goalId: string
  skillId: string
}

export const CompetencyContentList = ({
  detail,
  goalId,
  skillId,
}: CompetencyContentListProps) => {
  const recommendationActivityId = detail.recommendation?.activityId

  return (
    <ol
      aria-label='Conteúdos da Competência'
      className='relative space-y-3 before:absolute before:bottom-8 before:left-[22px] before:top-8 before:w-px before:bg-border lg:space-y-3 lg:before:left-6'
    >
      {detail.items.map((item: CompetencyDetailItem) => {
        const rowProps: CompetencyContentRowProps = {
          competencyId: detail.competencyId,
          goalId,
          isRecommended: item.kind === 'activity' && item.id === recommendationActivityId,
          item,
          skillId,
        }

        return <CompetencyContentRow key={`${item.kind}-${item.id}`} {...rowProps} />
      })}
    </ol>
  )
}
