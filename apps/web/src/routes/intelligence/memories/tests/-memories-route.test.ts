import { describe, expect, it, vi } from 'vitest'

import { requireAuthMiddleware } from '@/middlewares/require-auth-middleware'
import { Route, validateMemoriesSearch } from '../index'

const mocks = vi.hoisted(() => ({
  routeOptions: null as unknown,
  requireAuthMiddleware: vi.fn(),
}))

vi.mock('@tanstack/react-router', () => ({
  createFileRoute: vi.fn(() => (options: unknown) => {
    mocks.routeOptions = options
    return { options }
  }),
}))

vi.mock('@/middlewares/require-auth-middleware', () => ({
  requireAuthMiddleware: mocks.requireAuthMiddleware,
}))

vi.mock('@/ui/intelligence/widgets/pages/memories-page', () => ({
  MemoriesPage: () => null,
}))

type MemoriesRouteOptions = {
  beforeLoad: () => unknown
  validateSearch: typeof validateMemoriesSearch
}

const MEMORY_ID = '01J7T8AC91Z5K8M4JQ8C2D6F0B'

const routeOptions = () => mocks.routeOptions as MemoriesRouteOptions

describe('Memories route', () => {
  it('defaults to the list view without optional values', () => {
    expect(validateMemoriesSearch({})).toEqual({
      q: undefined,
      category: undefined,
      view: 'list',
      memory: undefined,
    })
  })

  it('keeps every valid search value', () => {
    expect(
      validateMemoriesSearch({
        q: '  python  ',
        category: 'recurring_difficulty',
        view: 'map',
        memory: MEMORY_ID,
      }),
    ).toEqual({
      q: 'python',
      category: 'recurring_difficulty',
      view: 'map',
      memory: MEMORY_ID,
    })
  })

  it.each([
    ['a blank query', { q: '   ' }],
    ['a query longer than 100 characters', { q: 'a'.repeat(101) }],
    ['a non-string query', { q: 12 }],
  ])('drops %s', (_description, search) => {
    expect(validateMemoriesSearch(search).q).toBeUndefined()
  })

  it('keeps a query of exactly 100 characters', () => {
    expect(validateMemoriesSearch({ q: 'a'.repeat(100) }).q).toBe('a'.repeat(100))
  })

  it.each([
    ['an unknown category', { category: 'all' }],
    ['a non-string category', { category: 3 }],
  ])('drops %s', (_description, search) => {
    expect(validateMemoriesSearch(search).category).toBeUndefined()
  })

  it.each([
    ['an unknown view', { view: 'grid' }],
    ['a non-string view', { view: 1 }],
  ])('falls back to the list view for %s', (_description, search) => {
    expect(validateMemoriesSearch(search).view).toBe('list')
  })

  it.each([
    ['a malformed memory', { memory: 'not-a-ulid' }],
    ['a memory with forbidden letters', { memory: '01J7T8AC91Z5K8M4JQ8C2D6F0I' }],
    ['a non-string memory', { memory: 7 }],
  ])('drops %s', (_description, search) => {
    expect(validateMemoriesSearch(search).memory).toBeUndefined()
  })

  it('registers the validator and runs the authentication middleware', () => {
    const route = routeOptions()
    mocks.requireAuthMiddleware.mockReturnValue('authorized')

    expect(Route).toBeDefined()
    expect(route.validateSearch).toBe(validateMemoriesSearch)
    expect(route.beforeLoad()).toBe('authorized')
    expect(vi.mocked(requireAuthMiddleware)).toHaveBeenCalledOnce()
  })
})
