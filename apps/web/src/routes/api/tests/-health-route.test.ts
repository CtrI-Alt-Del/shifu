import { describe, expect, it, vi } from 'vitest'

import { Route } from '../health'

const mocks = vi.hoisted(() => ({ routeOptions: null as unknown }))

vi.mock('@tanstack/react-router', () => ({
  createFileRoute: vi.fn(() => (options: unknown) => {
    mocks.routeOptions = options
    return { options }
  }),
}))

type HealthRouteOptions = {
  server: {
    handlers: {
      GET: () => Response
    }
  }
}

const routeOptions = () => mocks.routeOptions as HealthRouteOptions

describe('Web health route', () => {
  it('returns a deterministic JSON success response', async () => {
    expect(Route).toBeDefined()

    const response = await routeOptions().server.handlers.GET()

    expect(response.status).toBe(200)
    expect(response.headers.get('content-type')).toContain('application/json')
    await expect(response.json()).resolves.toEqual({ status: 'ok' })
  })
})
