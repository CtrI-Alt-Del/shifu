import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import axios, { type InternalAxiosRequestConfig } from 'axios'
import { createElement, type PropsWithChildren } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { EvolutionOption } from '@/core/learning/learning-panorama'
import type { SkillEvolution } from '@/core/learning/skill-evolution'

import { useSkillEvolutionCard } from '../use-skill-evolution-card'
import { getSkillEvolution } from '../use-skill-evolution-query'

vi.mock('@tanstack/react-start', () => {
  const builder = {
    middleware: () => builder,
    validator: () => builder,
    handler:
      (handler: (input: unknown) => Promise<unknown>) =>
      (input: { data?: unknown } = {}) =>
        handler({
          ...input,
          context: { requestId: 'request-1', telemetry: { emit: vi.fn() } },
        }),
  }
  return { createServerFn: () => builder }
})
vi.mock('@tanstack/react-start/server', () => ({
  getRequest: () => new Request('http://web.test/gamification'),
}))
vi.mock('@/start', () => ({ serverFunctionTelemetryMiddleware: {} }))
vi.mock('@/constants/server-env', () => ({
  SERVER_ENV: {
    shifuServerAppUrl: 'http://upstream.test',
    bffSharedSecret: 'server-owned-secret',
  },
}))
const session = vi.hoisted(() => ({ isSignedIn: true }))
vi.mock('@/provision/auth/better-auth/better-auth-provider', () => ({
  getBetterAuthProvider: () => ({
    getCurrentAccess: async () =>
      session.isSignedIn ? { accessToken: 'learner-access' } : null,
  }),
}))

const options: EvolutionOption[] = [
  {
    skillExperienceId: 'exp-python',
    goalTitle: 'Carreira em dados',
    skillName: 'Python para análise de dados',
    status: 'learning',
  },
  {
    skillExperienceId: 'exp-sql',
    goalTitle: 'Carreira em dados',
    skillName: 'SQL básico',
    status: 'diagnosing',
  },
]

const evolution: SkillEvolution = {
  skillExperienceId: 'exp-python',
  points: [
    { occurredAt: '2026-09-28T15:00:00Z', result: 42, isPartial: true, isBaseline: true },
    {
      occurredAt: '2026-10-05T15:00:00Z',
      result: 55,
      isPartial: false,
      isBaseline: false,
    },
  ],
}

// Keeps the consuming hook, query, service, request factory and Axios mapping
// real. Only the network adapter is replaced.
function installTransport(
  respond: (request: InternalAxiosRequestConfig) => [unknown, number],
) {
  const requests: InternalAxiosRequestConfig[] = []
  const createClient = axios.create.bind(axios)
  vi.spyOn(axios, 'create').mockImplementation((config) =>
    createClient({
      ...config,
      adapter: async (request) => {
        requests.push(request)
        const [data, status] = respond(request)
        return { data, status, statusText: '', headers: {}, config: request }
      },
    }),
  )
  return requests
}

function createQueryWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  })
  return function QueryWrapper({ children }: PropsWithChildren) {
    return createElement(QueryClientProvider, { client }, children)
  }
}

describe('useSkillEvolutionCard transport', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    session.isSignedIn = true
  })

  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('reads the default experience evolution with the learner access token', async () => {
    const requests = installTransport(() => [evolution, 200])

    const { result } = renderHook(
      () => useSkillEvolutionCard({ options, defaultSkillExperienceId: 'exp-python' }),
      { wrapper: createQueryWrapper() },
    )

    await waitFor(() => expect(result.current.state).toBe('success'))
    expect(result.current.evolutionData.map((datum) => datum.value)).toEqual([42, 55])
    expect(requests).toHaveLength(1)
    expect(requests[0].method).toBe('get')
    expect(requests[0].baseURL).toBe('http://upstream.test')
    expect(requests[0].url).toBe(
      '/learning/panorama/skill-experiences/exp-python/evolution',
    )
    expect(requests[0].headers.get('Authorization')).toBe('Bearer learner-access')
    expect(requests[0].headers.get('X-Shifu-Bff-Secret')).toBe('server-owned-secret')
    expect(requests[0].withCredentials).toBe(false)
  })

  it('reloads only the chosen experience when the selection changes', async () => {
    const requests = installTransport((request) => [
      {
        skillExperienceId: String(request.url).includes('exp-sql')
          ? 'exp-sql'
          : 'exp-python',
        points: String(request.url).includes('exp-sql') ? [] : evolution.points,
      },
      200,
    ])

    const { result } = renderHook(
      () => useSkillEvolutionCard({ options, defaultSkillExperienceId: 'exp-python' }),
      { wrapper: createQueryWrapper() },
    )
    await waitFor(() => expect(result.current.state).toBe('success'))

    act(() => result.current.handleSelectSkillExperience('exp-sql'))

    await waitFor(() => expect(result.current.state).toBe('empty'))
    expect(requests.map((request) => request.url)).toEqual([
      '/learning/panorama/skill-experiences/exp-python/evolution',
      '/learning/panorama/skill-experiences/exp-sql/evolution',
    ])
  })

  it('turns a failed read into the card error state and recovers on retry', async () => {
    let status = 503
    const requests = installTransport(() =>
      status === 200 ? [evolution, 200] : [{ message: 'Indisponível.' }, status],
    )

    const { result } = renderHook(
      () => useSkillEvolutionCard({ options, defaultSkillExperienceId: 'exp-python' }),
      { wrapper: createQueryWrapper() },
    )
    await waitFor(() => expect(result.current.state).toBe('error'))
    expect(result.current.evolutionData).toEqual([])

    status = 200
    act(() => result.current.handleRetry())

    await waitFor(() => expect(result.current.state).toBe('success'))
    expect(requests).toHaveLength(2)
  })

  it.each([401, 403])('maps an upstream %i into the card error state', async (status) => {
    installTransport(() => [{ message: 'Negado.' }, status])

    const { result } = renderHook(
      () => useSkillEvolutionCard({ options, defaultSkillExperienceId: 'exp-python' }),
      { wrapper: createQueryWrapper() },
    )

    await waitFor(() => expect(result.current.state).toBe('error'))
  })

  describe('server function', () => {
    it('returns the evolution of the requested experience', async () => {
      installTransport(() => [evolution, 200])

      await expect(
        getSkillEvolution({ data: { skillExperienceId: 'exp-python' } }),
      ).resolves.toEqual({
        kind: 'success',
        evolution,
      })
    })

    it('answers unauthorized without calling the upstream when there is no session', async () => {
      session.isSignedIn = false
      const requests = installTransport(() => [evolution, 200])

      await expect(
        getSkillEvolution({ data: { skillExperienceId: 'exp-python' } }),
      ).resolves.toEqual({ kind: 'unauthorized' })
      expect(requests).toHaveLength(0)
    })

    it('maps an upstream 401 to unauthorized', async () => {
      installTransport(() => [{ message: 'Sessão expirada.' }, 401])

      await expect(
        getSkillEvolution({ data: { skillExperienceId: 'exp-python' } }),
      ).resolves.toEqual({ kind: 'unauthorized' })
    })

    it('maps an upstream 403 to forbidden', async () => {
      installTransport(() => [{ message: 'Negado.' }, 403])

      await expect(
        getSkillEvolution({ data: { skillExperienceId: 'exp-python' } }),
      ).resolves.toEqual({ kind: 'forbidden' })
    })

    it('maps an unknown or foreign experience 404 to unavailable', async () => {
      installTransport(() => [{ message: 'Não encontrada.' }, 404])

      await expect(
        getSkillEvolution({ data: { skillExperienceId: 'exp-other' } }),
      ).resolves.toEqual({ kind: 'unavailable', statusCode: 404 })
    })

    it('maps any other upstream failure to unavailable with its status code', async () => {
      installTransport(() => [{ message: 'Indisponível.' }, 503])

      await expect(
        getSkillEvolution({ data: { skillExperienceId: 'exp-python' } }),
      ).resolves.toEqual({ kind: 'unavailable', statusCode: 503 })
    })
  })
})
