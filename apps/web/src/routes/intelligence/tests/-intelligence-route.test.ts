import { describe, expect, it, vi } from 'vitest'

import { requireAuthMiddleware } from '@/middlewares/require-auth-middleware'
import { Route, validateIntelligenceSearch } from '../index'

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

type IntelligenceRouteOptions = {
  beforeLoad: () => unknown
  validateSearch: typeof validateIntelligenceSearch
}

const routeOptions = () => mocks.routeOptions as IntelligenceRouteOptions

describe('Intelligence route', () => {
  it('keeps a valid ULID session search value', () => {
    expect(validateIntelligenceSearch({ session: '01J7T8AC91Z5K8M4JQ8C2D6F0B' })).toEqual(
      {
        session: '01J7T8AC91Z5K8M4JQ8C2D6F0B',
      },
    )
  })

  it.each([
    ['a malformed value', { session: 'not-a-ulid' }],
    ['a non-string value', { session: 123 }],
    ['a missing value', {}],
  ])('clears %s from the search state', (_description, search) => {
    expect(validateIntelligenceSearch(search)).toEqual({ session: undefined })
  })

  it('registers the validator and runs the authentication middleware', () => {
    const route = routeOptions()
    mocks.requireAuthMiddleware.mockReturnValue('authorized')

    expect(Route).toBeDefined()
    expect(route.validateSearch).toBe(validateIntelligenceSearch)
    expect(route.beforeLoad()).toBe('authorized')
    expect(vi.mocked(requireAuthMiddleware)).toHaveBeenCalledOnce()
  })
})
