import { act, cleanup, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { MEMORY_SEARCH_DEBOUNCE_MS, useMemoryFilters } from '../use-memory-filters'

const onQueryChangeMock = vi.fn()
const onCategoryChangeMock = vi.fn()

function renderFilters(query = '') {
  return renderHook(
    ({ query: currentQuery }) =>
      useMemoryFilters({
        query: currentQuery,
        onQueryChange: onQueryChangeMock,
        onCategoryChange: onCategoryChangeMock,
      }),
    { initialProps: { query } },
  )
}

describe('useMemoryFilters', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.clearAllMocks()
  })
  afterEach(() => {
    cleanup()
    vi.useRealTimers()
  })

  it('starts with the query from the URL and emits nothing', () => {
    const { result } = renderFilters('python')

    expect(result.current.draftQuery).toBe('python')
    act(() => vi.advanceTimersByTime(MEMORY_SEARCH_DEBOUNCE_MS * 2))
    expect(onQueryChangeMock).not.toHaveBeenCalled()
  })

  it('emits the trimmed query once after the debounce window', () => {
    const { result } = renderFilters()

    act(() => result.current.handleQueryInputChange('  fun'))
    act(() => vi.advanceTimersByTime(MEMORY_SEARCH_DEBOUNCE_MS - 1))
    act(() => result.current.handleQueryInputChange('  função  '))
    act(() => vi.advanceTimersByTime(MEMORY_SEARCH_DEBOUNCE_MS - 1))

    expect(onQueryChangeMock).not.toHaveBeenCalled()
    expect(result.current.draftQuery).toBe('  função  ')

    act(() => vi.advanceTimersByTime(1))

    expect(onQueryChangeMock).toHaveBeenCalledOnce()
    expect(onQueryChangeMock).toHaveBeenCalledWith('função')
  })

  it('does not emit when the trimmed query equals the current URL query', () => {
    const { result } = renderFilters('python')

    act(() => result.current.handleQueryInputChange('python  '))
    act(() => vi.advanceTimersByTime(MEMORY_SEARCH_DEBOUNCE_MS))

    expect(onQueryChangeMock).not.toHaveBeenCalled()
  })

  it('emits an empty query when the field is cleared', () => {
    const { result } = renderFilters('python')

    act(() => result.current.handleQueryInputChange(''))
    act(() => vi.advanceTimersByTime(MEMORY_SEARCH_DEBOUNCE_MS))

    expect(onQueryChangeMock).toHaveBeenCalledWith('')
  })

  it('replaces the draft when the URL query changes externally', () => {
    const { result, rerender } = renderFilters('python')

    rerender({ query: '' })

    expect(result.current.draftQuery).toBe('')
    act(() => vi.advanceTimersByTime(MEMORY_SEARCH_DEBOUNCE_MS))
    expect(onQueryChangeMock).not.toHaveBeenCalled()
  })

  it('keeps newer typing when the URL echoes an earlier emission', () => {
    const { result, rerender } = renderFilters()

    act(() => result.current.handleQueryInputChange('ab'))
    act(() => vi.advanceTimersByTime(MEMORY_SEARCH_DEBOUNCE_MS))
    act(() => result.current.handleQueryInputChange('abc'))
    rerender({ query: 'ab' })

    expect(result.current.draftQuery).toBe('abc')
  })

  it('maps the "all" category to a cleared filter and forwards real categories', () => {
    const { result } = renderFilters()

    act(() => result.current.handleCategorySelect('all'))
    act(() => result.current.handleCategorySelect('recurring_difficulty'))

    expect(onCategoryChangeMock).toHaveBeenNthCalledWith(1, null)
    expect(onCategoryChangeMock).toHaveBeenNthCalledWith(2, 'recurring_difficulty')
  })
})
