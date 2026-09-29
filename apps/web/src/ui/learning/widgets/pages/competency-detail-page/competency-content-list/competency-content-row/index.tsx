import { Link } from '@tanstack/react-router'

import type { CompetencyDetailItem } from '@/core/learning/competency-detail'
import { Icon } from '@/ui/shared/widgets/components/icon'
import { DIFFICULTY_STYLES } from '@/ui/learning/widgets/components/difficulty-badge/difficulty-badge-styles'

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
  targetConceptId?: string | null
}

export const CompetencyContentRow = ({
  competencyId,
  goalId,
  isRecommended,
  item,
  skillId,
  targetConceptId,
}: CompetencyContentRowProps) => {
  const concepts = item.concepts ?? []
  const conceptDescription =
    concepts.length > 0
      ? ` · Conceitos: ${concepts.map((concept) => `${concept.name}${isRecommended && concept.id === targetConceptId ? ' (Foco atual)' : ''}`).join(', ')}`
      : ''
  const conceptChips = concepts.length > 0 && (
    <span className='mt-2 flex min-w-0 flex-wrap gap-1.5'>
      {concepts.map((concept) => {
        const isCurrentFocus = isRecommended && concept.id === targetConceptId

        return (
          <span
            className={`max-w-full break-words rounded-md border px-2.5 py-0.5 text-xs leading-5 ${isCurrentFocus ? 'border-primary bg-primary/10 text-foreground' : 'border-control-border bg-muted text-muted-foreground'}`}
            key={concept.id}
          >
            {concept.name}
            {isCurrentFocus ? ' · Foco atual' : ''}
          </span>
        )
      })}
    </span>
  )

  if (item.kind === 'material') {
    return (
      <li className='relative flex gap-4 lg:gap-5'>
        <span className='relative z-10 grid size-11 shrink-0 place-items-center rounded-full border border-control-border bg-muted text-muted-foreground lg:size-12'>
          <Icon name='book-open' size={20} />
        </span>
        <Link
          aria-label={`${item.title} — Material de apoio${conceptDescription}`}
          className={`group flex min-h-16 min-w-0 flex-1 items-center justify-between gap-4 rounded-md border px-4 py-3 transition-colors lg:min-h-[68px] lg:px-5 ${isRecommended ? 'border-primary bg-primary/5 hover:bg-primary/10' : 'border-border bg-card hover:border-control-border hover:bg-muted'}`}
          params={{ goalId, skillId, competencyId, materialId: item.id }}
          to='/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/materials/$materialId'
        >
          <span className='min-w-0 flex-1'>
            <span className='block break-words font-semibold text-foreground'>
              {item.title}
            </span>
            <span className='mt-1 block text-sm text-muted-foreground'>
              {isRecommended ? 'Material de apoio · Opcional' : 'Material de apoio'}
            </span>
            {conceptChips}
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
          isRecommended
            ? `Praticar ${item.title}${conceptDescription}`
            : `${item.title} — ${metadata}${conceptDescription}`
        }
        className={`group flex min-h-16 min-w-0 flex-1 items-center justify-between gap-4 rounded-md border px-4 py-3 transition-colors lg:min-h-[68px] lg:px-5 ${
          isRecommended
            ? 'border-primary bg-primary/5 hover:bg-primary/10'
            : 'border-border bg-card hover:border-control-border hover:bg-muted'
        }`}
        params={{ activityId: item.id, competencyId, goalId, skillId }}
        to='/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId'
      >
        <span className='min-w-0 flex-1'>
          <span className='block break-words font-semibold text-foreground'>
            {item.title}
          </span>
          <span
            className={`mt-1 block text-sm ${isRecommended ? 'text-selo-text' : 'text-muted-foreground'}`}
          >
            {isRecommended ? (
              <>
                {activityLabel} ·{' '}
                <span className={DIFFICULTY_STYLES[item.difficulty].text}>
                  {DIFFICULTY_LABELS[item.difficulty]}
                </span>{' '}
                · Recomendada
              </>
            ) : (
              <>
                {activityLabel} ·{' '}
                <span className={DIFFICULTY_STYLES[item.difficulty].text}>
                  {DIFFICULTY_LABELS[item.difficulty]}
                </span>
                {item.latestScore === null ? '' : ` · Nota ${item.latestScore}`}
              </>
            )}
          </span>
          {conceptChips}
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
