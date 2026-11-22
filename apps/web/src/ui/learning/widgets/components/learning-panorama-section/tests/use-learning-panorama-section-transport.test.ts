import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, renderHook, waitFor } from '@testing-library/react'
import axios, { type InternalAxiosRequestConfig } from 'axios'
import { createElement, type PropsWithChildren } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { LearningPanorama } from '@/core/learning/learning-panorama'
import { getLearningPanorama } from '@/ui/learning/hooks/use-learning-panorama-query'

import { useLearningPanoramaSection } from '../use-learning-panorama-section'

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

const panorama: LearningPanorama = {
  hasGoals: true,
  completedSkillCount: 3,
  masteredCompetencyCount: 14,
  stageDistribution: {
    notStarted: 2,
    diagnosing: 1,
    learning: 3,
    completed: 3,
    goalCount: 3,
  },
  resumeItems: [],
  weeklyEvaluatedActivities: [{ weekStart: '2026-09-28', count: 3 }],
  evolutionOptions: [],
  defaultEvolutionSkillExperienceId: null,
  completedSkills: [],
  recentMasteries: [],
}

// Keeps the consuming hook, query, service, request factory and Axios mapping
// real. Only the network adapter is replaced.
function installTransport(body: unknown, status = 200) {
  const requests: InternalAxiosRequestConfig[] = []
  const createClient = axios.create.bind(axios)
  vi.spyOn(axios, 'create').mockImplementation((config) =>
    createClient({
      ...config,
      adapter: async (request) => {
        requests.push(request)
        return { data: body, status, statusText: '', headers: {}, config: request }
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

describe('useLearningPanoramaSection transport', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    session.isSignedIn = true
  })

  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('maps the authenticated upstream read into the section state', async () => {
    const requests = installTransport(panorama)

    const { result } = renderHook(() => useLearningPanoramaSection(), {
      wrapper: createQueryWrapper(),
    })

    await waitFor(() => {
      expect(result.current.state).toBe('success')
      expect(result.current.panorama).toEqual(panorama)
    })
    expect(requests).toHaveLength(1)
    expect(requests[0].method).toBe('get')
    expect(requests[0].baseURL).toBe('http://upstream.test')
    expect(requests[0].url).toBe('/learning/panorama')
    expect(requests[0].headers.get('Authorization')).toBe('Bearer learner-access')
    expect(requests[0].headers.get('X-Shifu-Bff-Secret')).toBe('server-owned-secret')
    expect(requests[0].withCredentials).toBe(false)
  })

  it('turns an unavailable upstream into the error state without success data', async () => {
    const requests = installTransport({ message: 'Indisponível.' }, 503)

    const { result } = renderHook(() => useLearningPanoramaSection(), {
      wrapper: createQueryWrapper(),
    })

    await waitFor(() => {
      expect(result.current.state).toBe('error')
      expect(result.current.panorama).toBeNull()
    })
    expect(requests).toHaveLength(1)
  })

  it.each([401, 403])('maps an upstream %i into the error state', async (status) => {
    installTransport({ message: 'Negado.' }, status)

    const { result } = renderHook(() => useLearningPanoramaSection(), {
      wrapper: createQueryWrapper(),
    })

    await waitFor(() => {
      expect(result.current.state).toBe('error')
      expect(result.current.panorama).toBeNull()
    })
  })

  describe('server function', () => {
    it('returns the panorama read with the learner access token', async () => {
      installTransport(panorama)

      await expect(getLearningPanorama()).resolves.toEqual({ kind: 'success', panorama })
    })

    it('answers unauthorized without calling the upstream when there is no session', async () => {
      session.isSignedIn = false
      const requests = installTransport(panorama)

      await expect(getLearningPanorama()).resolves.toEqual({ kind: 'unauthorized' })
      expect(requests).toHaveLength(0)
    })

    it('maps an upstream 401 to unauthorized', async () => {
      installTransport({ message: 'Sessão expirada.' }, 401)

      await expect(getLearningPanorama()).resolves.toEqual({ kind: 'unauthorized' })
    })

    it('maps an upstream 403 to forbidden', async () => {
      installTransport({ message: 'Negado.' }, 403)

      await expect(getLearningPanorama()).resolves.toEqual({ kind: 'forbidden' })
    })

    it('maps any other upstream failure to unavailable with its status code', async () => {
      installTransport({ message: 'Indisponível.' }, 503)

      await expect(getLearningPanorama()).resolves.toEqual({
        kind: 'unavailable',
        statusCode: 503,
      })
    })
  })
})
