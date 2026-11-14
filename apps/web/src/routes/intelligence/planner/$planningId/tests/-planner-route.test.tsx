import { cleanup, render, screen } from '@testing-library/react'
import type { ReactElement } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { requireAuthMiddleware } from '@/middlewares/require-auth-middleware'
import type { PlannerPageProps } from '@/ui/intelligence/widgets/pages/planner-page'

import { Route } from '../index'

const PLANNING_ID = '01ARZ3NDEKTSV4RRFFQ69G5FAV'

const mocks = vi.hoisted(() => ({
  routeOptions: null as unknown,
  requireAuthMiddleware: vi.fn(),
}))

vi.mock('@tanstack/react-router', () => ({
  createFileRoute: vi.fn(() => (options: unknown) => {
    mocks.routeOptions = options
    return { options, useParams: () => ({ planningId: PLANNING_ID }) }
  }),
}))

vi.mock('@/middlewares/require-auth-middleware', () => ({
  requireAuthMiddleware: mocks.requireAuthMiddleware,
}))

vi.mock('@/ui/intelligence/widgets/pages/planner-page', () => ({
  PlannerPage: ({ planningId }: PlannerPageProps) => <p>Planejamento {planningId}</p>,
}))

type PlannerRouteOptions = {
  beforeLoad: () => unknown
  component: () => ReactElement
}

const routeOptions = () => mocks.routeOptions as PlannerRouteOptions

describe('Planner route', () => {
  afterEach(cleanup)

  it('runs the authentication middleware before loading', () => {
    mocks.requireAuthMiddleware.mockReturnValue('authorized')

    expect(Route).toBeDefined()
    expect(routeOptions().beforeLoad()).toBe('authorized')
    expect(vi.mocked(requireAuthMiddleware)).toHaveBeenCalledOnce()
  })

  it('renders the planner page with the routed planning id', () => {
    const RouteComponent = routeOptions().component

    render(<RouteComponent />)

    expect(screen.getByText(`Planejamento ${PLANNING_ID}`)).toBeVisible()
  })
})
