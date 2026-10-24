import { createFileRoute } from '@tanstack/react-router'

import {
  LEARNER_MEMORY_CATEGORIES,
  type LearnerMemoryCategory,
} from '@/core/intelligence/learner-memory'
import { MemoriesPage } from '@/ui/intelligence/widgets/pages/memories-page'
import { requireAuthMiddleware } from '@/middlewares/require-auth-middleware'

const ULID_PATTERN = /^[0-7][0-9A-HJKMNP-TV-Z]{25}$/
const MAX_QUERY_LENGTH = 100

export type MemoriesSearch = {
  q?: string
  category?: LearnerMemoryCategory
  view: 'list' | 'map'
  memory?: string
}

export function validateMemoriesSearch(search: Record<string, unknown>): MemoriesSearch {
  const query = typeof search.q === 'string' ? search.q.trim() : ''
  const category = LEARNER_MEMORY_CATEGORIES.find((value) => value === search.category)
  const memory =
    typeof search.memory === 'string' && ULID_PATTERN.test(search.memory)
      ? search.memory
      : undefined

  return {
    q: query && query.length <= MAX_QUERY_LENGTH ? query : undefined,
    category,
    view: search.view === 'map' ? 'map' : 'list',
    memory,
  }
}

export const Route = createFileRoute('/intelligence/memories/')({
  beforeLoad: () => requireAuthMiddleware(),
  validateSearch: validateMemoriesSearch,
  component: MemoriesPage,
})
