import type { ActivityDifficulty } from '@/core/learning/competency-detail'

type DifficultyBadgeProps = { difficulty: ActivityDifficulty }

const DIFFICULTY_LABELS = {
  easy: 'Fácil',
  medium: 'Média',
  hard: 'Difícil',
} satisfies Record<ActivityDifficulty, string>

const DIFFICULTY_STYLES = {
  easy: 'bg-success/15 text-success',
  medium: 'bg-amber-400/15 text-amber-300',
  hard: 'bg-danger/15 text-selo-text',
} satisfies Record<ActivityDifficulty, string>

export const DifficultyBadge = ({ difficulty }: DifficultyBadgeProps) => (
  <span
    className={`rounded-md px-2.5 py-1 text-xs font-medium ${DIFFICULTY_STYLES[difficulty]}`}
  >
    {DIFFICULTY_LABELS[difficulty]}
  </span>
)
