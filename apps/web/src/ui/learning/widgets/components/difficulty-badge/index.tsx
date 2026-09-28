import type { ActivityDifficulty } from '@/core/learning/competency-detail'
import { DIFFICULTY_STYLES } from './difficulty-badge-styles'

type DifficultyBadgeProps = { difficulty: ActivityDifficulty }

const DIFFICULTY_LABELS = {
  easy: 'Fácil',
  medium: 'Média',
  hard: 'Difícil',
} satisfies Record<ActivityDifficulty, string>

export const DifficultyBadge = ({ difficulty }: DifficultyBadgeProps) => (
  <span
    className={`rounded-md px-2.5 py-1 text-xs font-medium ${DIFFICULTY_STYLES[difficulty].badge}`}
  >
    {DIFFICULTY_LABELS[difficulty]}
  </span>
)
