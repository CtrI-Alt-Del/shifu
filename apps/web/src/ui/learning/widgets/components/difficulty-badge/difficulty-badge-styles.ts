import type { ActivityDifficulty } from '@/core/learning/competency-detail'

export const DIFFICULTY_STYLES = {
  easy: { badge: 'bg-success/15 text-success', text: 'text-success' },
  medium: { badge: 'bg-amber-400/15 text-amber-300', text: 'text-amber-300' },
  hard: { badge: 'bg-danger/15 text-selo-text', text: 'text-selo-text' },
} satisfies Record<ActivityDifficulty, { badge: string; text: string }>
