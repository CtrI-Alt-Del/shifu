import { Link } from '@tanstack/react-router'

import type { CompetencyDetailItem } from '@/core/learning/competency-detail'
import { Icon } from '@/ui/shared/widgets/components/icon'

const DIFFICULTY_LABELS = {
  easy: 'Fácil',
  medium: 'Média',
  hard: 'Difícil',
} as const

const ACTIVITY_TYPE_LABELS: Record<string, string> = {
  diagnostic: 'Diagnóstico',
  learning: 'Atividade',
  review: 'Revisão',
}

export type CompetencyContentRowProps = {
  competencyId: string
  goalId: string
  isRecommended: boolean
  item: CompetencyDetailItem
  skillId: string
}

export const CompetencyContentRow = ({
  competencyId,
  goalId,
  isRecommended,
  item,
  skillId,
}: CompetencyContentRowProps) => {
  if (item.kind === 'material') {
    return (
      <li className='relative flex gap-4 lg:gap-5'>
        <span className='relative z-10 grid size-11 shrink-0 place-items-center rounded-full border border-control-border bg-muted text-muted-foreground lg:size-12'>
          <Icon name='book-open' size={20} />
        </span>
        <Link
          aria-label={`${item.title} — Material de apoio`}
          className='group flex min-h-16 min-w-0 flex-1 items-center justify-between gap-4 rounded-md border border-border bg-card px-4 py-3 transition-colors hover:border-control-border hover:bg-muted lg:min-h-[68px] lg:px-5'
          params={{ goalId, skillId, competencyId, materialId: item.id }}
          to='/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/materials/$materialId'
        >
          <span className='min-w-0'>
            <span className='block break-words font-semibold text-foreground'>
              {item.title}
            </span>
            <span className='mt-1 block text-sm text-muted-foreground'>
              Material de apoio
            </span>
          </span>
          <Icon
            className='shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5'
            name='chevron-right'
            size={18}
          />
        </Link>
      </li>
    )
  }

  const activityLabel = ACTIVITY_TYPE_LABELS[item.activityType] ?? 'Atividade'
  const metadata = `${activityLabel} · ${DIFFICULTY_LABELS[item.difficulty]}${
    item.latestScore === null ? '' : ` · Nota ${item.latestScore}`
  }`

  return (
    <li className='relative flex gap-4 lg:gap-5'>
      <span
        className={`relative z-10 grid size-11 shrink-0 place-items-center rounded-full border lg:size-12 ${
          isRecommended
            ? 'border-primary bg-accent text-selo-text'
            : 'border-success/60 bg-success/10 text-success'
        }`}
      >
        <Icon name='target' size={20} />
      </span>
      <Link
        aria-label={
          isRecommended ? `Praticar ${item.title}` : `${item.title} — ${metadata}`
        }
        className={`group flex min-h-16 min-w-0 flex-1 items-center justify-between gap-4 rounded-md border px-4 py-3 transition-colors lg:min-h-[68px] lg:px-5 ${
          isRecommended
            ? 'border-primary bg-primary/5 hover:bg-primary/10'
            : 'border-border bg-card hover:border-control-border hover:bg-muted'
        }`}
        params={{ activityId: item.id, competencyId, goalId, skillId }}
        to='/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId'
      >
        <span className='min-w-0'>
          <span className='block break-words font-semibold text-foreground'>
            {item.title}
          </span>
          <span
            className={`mt-1 block text-sm ${isRecommended ? 'text-selo-text' : 'text-success'}`}
          >
            {isRecommended
              ? `${DIFFICULTY_LABELS[item.difficulty]} · Recomendada`
              : metadata}
          </span>
        </span>
        {isRecommended ? (
          <span className='inline-flex min-h-11 shrink-0 items-center justify-center rounded-md bg-primary px-4 font-bold text-primary-foreground'>
            Praticar
          </span>
        ) : (
          <Icon
            className='shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5'
            name='chevron-right'
            size={18}
          />
        )}
      </Link>
    </li>
  )
}
