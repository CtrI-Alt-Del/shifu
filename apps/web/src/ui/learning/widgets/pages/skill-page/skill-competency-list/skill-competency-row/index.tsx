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

export const SkillCompetencyRow = ({
  competency,
  goalId,
  skillId,
  onBlockedSelect,
}: SkillCompetencyRowProps) => {
  const isBlocked = competency.availability === 'unavailable'
  const isMastered = competency.status === 'mastered'
  const progress = Math.round(competency.progress)
  const statusLabel = COMPETENCY_STATUS_LABELS[competency.status]

  const content = (
    <>
      <span
        className={`w-5 shrink-0 text-[13px] ${
          competency.isFocus ? 'text-selo-text' : 'text-muted-foreground'
        }`}
      >
        {competency.position}
      </span>
      <span
        className={`min-w-0 flex-1 truncate text-[15px] font-medium lg:w-[280px] lg:flex-none ${
          isBlocked ? 'text-secondary-foreground' : 'text-foreground'
        }`}
      >
        {competency.competencyName}
      </span>

      <span
        aria-hidden='true'
        className={`relative hidden h-2 w-[360px] shrink-0 overflow-hidden rounded-[3px] lg:block ${
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

      <span
        className={`w-10 shrink-0 text-right text-sm tabular-nums ${
          isBlocked ? 'text-secondary-foreground' : 'text-foreground'
        }`}
      >
        {progress}%
      </span>

      <span className='flex shrink-0 items-center gap-2 lg:mr-auto'>
        {isMastered ? (
          <span className='rounded-md bg-jade-solid px-2 py-1 text-[11px] font-medium text-on-jade'>
            {statusLabel}
          </span>
        ) : (
          <span className='rounded-md bg-jade-tint px-2 py-1 text-[11px] font-medium text-jade-text'>
            {statusLabel}
          </span>
        )}
        {competency.isFocus ? (
          <span className='rounded-md bg-accent px-2 py-1 text-[11px] font-medium text-selo-text'>
            Em foco
          </span>
        ) : null}
        {isBlocked ? (
          <span className='inline-flex items-center gap-1.5 rounded-md bg-muted px-2 py-1 text-[11px] font-medium text-secondary-foreground'>
            <Icon name='lock-keyhole' size={12} />
            Bloqueada
          </span>
        ) : null}
      </span>
    </>
  )

  const rowClassName = `flex min-h-[50px] w-full items-center gap-4 rounded-md px-4 py-[14px] text-left transition-colors ${
    competency.isFocus ? 'bg-muted' : ''
  }`

  if (isBlocked) {
    return (
      <li>
        <button
          aria-describedby='skill-blocked-hint'
          className={`${rowClassName} hover:bg-muted/60`}
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
        className={`${rowClassName} hover:bg-muted/60`}
        params={{ competencyId: competency.competencyId, goalId, skillId }}
        to='/learning/goals/$goalId/skills/$skillId/competencies/$competencyId'
      >
        {content}
      </Link>
    </li>
  )
}
