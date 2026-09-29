import { Link } from '@tanstack/react-router'

import {
  COMPETENCY_STATUS_LABELS,
  type SkillCompetencySummary,
} from '@/core/learning/skill-experience'
import { Icon } from '@/ui/shared/widgets/components/icon'

export type SkillCompetencyRowProps = {
  competency: SkillCompetencySummary
  goalId: string
  skillId: string
  onBlockedSelect: (competency: SkillCompetencySummary) => void
}

const THRESHOLDS = [40, 70, 85] as const
const BADGE = 'rounded-md px-2 py-1 text-xs font-medium lg:px-2.5 lg:py-1 lg:text-[13px]'
const ROW =
  'flex w-full flex-col gap-[7px] rounded-md px-2.5 py-[9px] text-left transition-colors hover:bg-muted/60 lg:min-h-[50px] lg:flex-row lg:items-center lg:gap-4 lg:px-4 lg:py-[14px]'

export const SkillCompetencyRow = ({
  competency,
  goalId,
  skillId,
  onBlockedSelect,
}: SkillCompetencyRowProps) => {
  const isBlocked = competency.availability === 'unavailable'
  const progress = competency.progress === null ? 0 : Math.round(competency.progress)
  const isMastered = competency.status === 'mastered' && progress >= 85
  const statusLabel =
    competency.progress === null
      ? 'Sem evidência'
      : COMPETENCY_STATUS_LABELS[
          isMastered
            ? 'mastered'
            : progress >= 70
              ? 'proficient'
              : progress >= 40
                ? 'developing'
                : 'learning'
        ]
  const rowClassName = competency.isFocus ? `${ROW} bg-muted` : ROW

  const content = (
    <>
      <span className='flex min-w-0 items-center gap-2 lg:contents'>
        <span
          className={`w-5 shrink-0 text-sm lg:order-1 lg:w-5 ${
            competency.isFocus ? 'text-selo-text' : 'text-muted-foreground'
          }`}
        >
          {competency.position}
        </span>
        <span
          className={`min-w-0 flex-1 truncate text-sm font-medium lg:order-2 lg:w-[280px] lg:flex-none lg:text-base ${
            isBlocked ? 'text-secondary-foreground' : 'text-foreground'
          }`}
        >
          {competency.competencyName}
        </span>
        <span
          className={`w-10 shrink-0 text-right text-sm tabular-nums lg:order-4 lg:w-10 lg:text-base ${
            isBlocked ? 'text-secondary-foreground' : 'text-foreground'
          }`}
        >
          {competency.progress === null ? 'Sem evidência' : `${progress}%`}
        </span>
      </span>

      <span
        aria-hidden='true'
        className={`relative h-2 w-full overflow-hidden rounded-[3px] lg:order-3 lg:w-[360px] lg:shrink-0 ${
          competency.isFocus ? 'bg-surface-alt' : 'bg-muted'
        }`}
      >
        <span
          className={`absolute inset-y-[1px] left-0 rounded-[3px] ${
            isBlocked
              ? 'bg-control-border'
              : isMastered
                ? 'bg-jade-solid'
                : 'bg-jade-fill'
          }`}
          style={{ width: `${Math.max(0, Math.min(100, progress))}%` }}
        />
        {THRESHOLDS.map((threshold) => (
          <span
            className='absolute inset-y-0 w-px bg-foreground'
            key={threshold}
            style={{ left: `${threshold}%` }}
          />
        ))}
      </span>

      <span className='flex shrink-0 flex-wrap items-center gap-1.5 lg:order-5 lg:mr-auto lg:gap-2'>
        {isMastered ? (
          <span className={`${BADGE} bg-jade-solid text-on-jade`}>{statusLabel}</span>
        ) : (
          <span className={`${BADGE} bg-jade-tint text-jade-text`}>{statusLabel}</span>
        )}
        {competency.isFocus ? (
          <span className={`${BADGE} bg-accent text-selo-text`}>Em foco</span>
        ) : null}
        {isBlocked ? (
          <span
            className={`${BADGE} inline-flex items-center gap-1.5 bg-muted text-secondary-foreground`}
          >
            <Icon name='lock-keyhole' size={11} />
            Bloqueada
          </span>
        ) : null}
      </span>
    </>
  )

  if (isBlocked) {
    return (
      <li>
        <button
          aria-describedby='skill-blocked-hint'
          className={rowClassName}
          onClick={() => onBlockedSelect(competency)}
          type='button'
        >
          {content}
        </button>
      </li>
    )
  }

  return (
    <li>
      <Link
        className={rowClassName}
        params={{ competencyId: competency.competencyId, goalId, skillId }}
        to='/learning/goals/$goalId/skills/$skillId/competencies/$competencyId'
      >
        {content}
      </Link>
    </li>
  )
}
