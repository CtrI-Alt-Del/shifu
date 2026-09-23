import type { ReactNode } from 'react'

interface SkillFoundationRowProps {
  skillId: string
  name: string
  status: 'present' | 'missing'
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
  const statusClass = status === 'present' ? 'text-green-600' : 'text-gray-500'

  if (isSelectable) {
    return (
      <div
        className='flex items-center gap-3 p-3 rounded border hover:bg-gray-50 cursor-pointer'
        onClick={() => onToggle?.(skillId)}
      >
        <input
          type='checkbox'
          checked={isSelected}
          onChange={() => onToggle?.(skillId)}
          className='w-4 h-4'
        />
        <div className='flex-1'>
          <div className='font-medium'>{name}</div>
          <div className={`text-sm ${statusClass}`}>{statusLabel}</div>
        </div>
      </div>
    )
  }

  return (
    <div className='flex items-center justify-between p-2 text-sm'>
      <span>{name}</span>
      <span className={statusClass}>{statusLabel}</span>
    </div>
  )
}
