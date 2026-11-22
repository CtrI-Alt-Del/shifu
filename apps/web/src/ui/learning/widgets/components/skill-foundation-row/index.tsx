import type { ReactNode } from 'react'

import type { SkillFoundationStatus } from '@/core/learning/skill-foundation-status'

type SkillFoundationRowProps = {
  skillId: string
  name: string
  status: SkillFoundationStatus
  isSelectable?: boolean
  isSelected?: boolean
  onToggle?: (skillId: string) => void
}

export function SkillFoundationRow({
  skillId,
  name,
  status,
  isSelectable = false,
  isSelected = false,
  onToggle,
}: SkillFoundationRowProps): ReactNode {
  const statusLabel = status === 'present' ? '✓ Presente' : '○ Ausente'
  const statusClass = status === 'present' ? 'text-jade-text' : 'text-muted-foreground'

  if (isSelectable) {
    return (
      <label className='flex min-h-11 cursor-pointer items-center gap-3 rounded-md border border-control-border bg-muted p-3 transition-colors hover:bg-accent has-[:checked]:border-selo-text has-[:checked]:bg-accent has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-ring'>
        <input
          checked={isSelected}
          className='size-4 accent-primary'
          data-focus-ring='delegated'
          onChange={() => onToggle?.(skillId)}
          type='checkbox'
        />
        <div className='flex-1'>
          <div className='font-medium text-foreground'>{name}</div>
          <div className={`text-sm ${statusClass}`}>{statusLabel}</div>
        </div>
      </label>
    )
  }

  return (
    <div className='flex items-center justify-between p-2 text-sm text-foreground'>
      <span>{name}</span>
      <span className={statusClass}>{statusLabel}</span>
    </div>
  )
}
