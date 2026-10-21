import { useEffect, useRef, useState } from 'react'

import type { LearnerMemoryCategory } from '@/core/intelligence/learner-memory'

export const MEMORY_SEARCH_DEBOUNCE_MS = 300
export const MEMORY_SEARCH_MAX_LENGTH = 100

export type MemoryCategoryFilter = LearnerMemoryCategory | 'all'

export type UseMemoryFiltersInput = {
  query: string
  onQueryChange: (query: string) => void
  onCategoryChange: (category: LearnerMemoryCategory | null) => void
}

export function useMemoryFilters({
  query,
  onQueryChange,
  onCategoryChange,
}: UseMemoryFiltersInput) {
  const [draftQuery, setDraftQuery] = useState(query)
  const lastEmittedQuery = useRef(query)
  const onQueryChangeRef = useRef(onQueryChange)
  onQueryChangeRef.current = onQueryChange

  // The URL is the source of truth: an external change (back navigation, clear
  // filters) replaces the draft, but the echo of our own emission does not.
  useEffect(
    function syncDraftFromUrl() {
      if (query === lastEmittedQuery.current) return
      lastEmittedQuery.current = query
      setDraftQuery(query)
    },
    [query],
  )

  useEffect(
    function emitDebouncedQuery() {
      const trimmedQuery = draftQuery.trim()
      if (trimmedQuery === lastEmittedQuery.current) return
      const timer = window.setTimeout(() => {
        lastEmittedQuery.current = trimmedQuery
        onQueryChangeRef.current(trimmedQuery)
      }, MEMORY_SEARCH_DEBOUNCE_MS)
      return () => window.clearTimeout(timer)
    },
    [draftQuery],
  )

  function handleQueryInputChange(value: string) {
    setDraftQuery(value)
  }

  function handleCategorySelect(value: MemoryCategoryFilter) {
    onCategoryChange(value === 'all' ? null : value)
  }

  return { draftQuery, handleQueryInputChange, handleCategorySelect }
}
