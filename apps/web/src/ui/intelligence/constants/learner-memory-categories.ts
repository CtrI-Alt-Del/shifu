import {
  LEARNER_MEMORY_CATEGORIES,
  type LearnerMemoryCategory,
} from '@/core/intelligence/learner-memory'
import type { IconName } from '@/ui/shared/widgets/components/icon'

export type LearnerMemoryCategoryPresentation = {
  /** Label used by chips, rows, menus and markers. */
  label: string
  /** Singular label used as the details caption. */
  detailLabel: string
  icon: IconName
}

export const LEARNER_MEMORY_CATEGORY_PRESENTATION: Record<
  LearnerMemoryCategory,
  LearnerMemoryCategoryPresentation
> = {
  explanation_preference: {
    label: 'Preferência de explicação',
    detailLabel: 'Preferência de explicação',
    icon: 'sliders-horizontal',
  },
  declared_knowledge: {
    label: 'Conhecimento declarado',
    detailLabel: 'Conhecimento declarado',
    icon: 'book-open',
  },
  interest_or_intention: {
    label: 'Interesse ou intenção',
    detailLabel: 'Interesse ou intenção',
    icon: 'compass',
  },
  recurring_difficulty: {
    label: 'Dificuldades recorrentes',
    detailLabel: 'Dificuldade recorrente',
    icon: 'puzzle',
  },
}

export const LEARNER_MEMORY_CATEGORY_OPTIONS = LEARNER_MEMORY_CATEGORIES.map(
  (category) => ({ category, ...LEARNER_MEMORY_CATEGORY_PRESENTATION[category] }),
)
