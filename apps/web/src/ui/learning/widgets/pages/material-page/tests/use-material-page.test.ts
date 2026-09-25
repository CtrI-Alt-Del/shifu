import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useQuery } from '@tanstack/react-query'

import { AuthError } from '@/core/errors/auth-error'
import type { MaterialDetail } from '@/core/learning/material-detail'
import { RestError } from '@/core/errors/rest-error'
import { useNavigation } from '@/ui/shared/hooks/use-navigation'

import { useMaterialPage } from '../use-material-page'

const { getMaterialDetailActionMock } = vi.hoisted(() => ({
  getMaterialDetailActionMock: vi.fn(),
}))

vi.mock('@tanstack/react-query', () => ({
  useQuery: vi.fn(),
}))

vi.mock('@/ui/shared/hooks/use-navigation', () => ({
  useNavigation: vi.fn(),
}))

vi.mock('@tanstack/react-start', () => ({
  createServerFn: () => ({
    validator: () => ({
      handler: () => getMaterialDetailActionMock,
    }),
  }),
}))

const useQueryMock = vi.mocked(useQuery)
const useNavigationMock = vi.mocked(useNavigation)

const props = {
  competencyId: '01SHF000000000000000000004',
  goalId: '01SHF000000000000000000012',
  materialId: '01SHF000000000000000000006',
  skillId: '01SHF000000000000000000002',
}

const activityId = '01SHF000000000000000000005'

const detail: MaterialDetail = {
  availability: 'available',
  competencyId: props.competencyId,
  competencyName: 'Variáveis e valores',
  content: 'Conteúdo oficial.',
  goalId: props.goalId,
  materialId: props.materialId,
  materialTitle: 'Nomeando valores',
  recommendation: null,
  skillId: props.skillId,
  skillName: 'Lógica de programação',
}

const navigateToMock = vi.fn()
const navigateToActivityMock = vi.fn(() => Promise.resolve())
const refetchMock = vi.fn(() => Promise.resolve({} as never))

function mockQuery(
  overrides: {
    data?: MaterialDetail | null
    error?: Error | null
    isPending?: boolean
  } = {},
) {
  useQueryMock.mockReturnValue({
    data: null,
    error: null,
    isPending: false,
    refetch: refetchMock,
    ...overrides,
  } as never)
}

describe('useMaterialPage', () => {
  beforeEach(() => {
    getMaterialDetailActionMock.mockReset()
    navigateToMock.mockReset()
    navigateToActivityMock.mockReset()
    navigateToActivityMock.mockResolvedValue(undefined)
    refetchMock.mockReset()
    useQueryMock.mockReset()
    useNavigationMock.mockReturnValue({
      navigateTo: navigateToMock,
      navigateToActivity: navigateToActivityMock,
      navigateToGoalDetail: vi.fn(),
      navigateToPlanner: vi.fn(),
    })
    mockQuery()
  })

  it('scopes the query key to the full material context', () => {
    renderHook(() => useMaterialPage(props))

    const options = useQueryMock.mock.calls[0]?.[0]

    expect(options?.queryKey).toEqual([
      'learning',
      'material-detail',
      props.goalId,
      props.skillId,
      props.competencyId,
      props.materialId,
    ])
  })

  it('requests the material with every identifier of the route', async () => {
    getMaterialDetailActionMock.mockResolvedValue(detail)
    renderHook(() => useMaterialPage(props))

    const queryFn = useQueryMock.mock.calls[0]?.[0]
      ?.queryFn as () => Promise<MaterialDetail>

    await expect(queryFn()).resolves.toEqual(detail)
    expect(getMaterialDetailActionMock).toHaveBeenCalledWith({ data: props })
  })

  it('maps a private absence to a not-found rejection', async () => {
    getMaterialDetailActionMock.mockResolvedValue({ kind: 'not-found' })
    renderHook(() => useMaterialPage(props))

    const queryFn = useQueryMock.mock.calls[0]?.[0]
      ?.queryFn as () => Promise<MaterialDetail>

    await expect(queryFn()).rejects.toThrow(RestError)
  })

  it('maps an invalid request to an unprocessable rejection', async () => {
    getMaterialDetailActionMock.mockResolvedValue({ kind: 'invalid-request' })
    renderHook(() => useMaterialPage(props))

    const queryFn = useQueryMock.mock.calls[0]?.[0]
      ?.queryFn as () => Promise<MaterialDetail>

    await expect(queryFn()).rejects.toMatchObject({ statusCode: 422 })
  })

  it('maps a rejected session to an authentication rejection', async () => {
    getMaterialDetailActionMock.mockResolvedValue({ kind: 'unauthorized' })
    renderHook(() => useMaterialPage(props))

    const queryFn = useQueryMock.mock.calls[0]?.[0]
      ?.queryFn as () => Promise<MaterialDetail>

    await expect(queryFn()).rejects.toThrow(AuthError)
  })

  it('reports a private absence separately from a recoverable error', () => {
    mockQuery({ error: new RestError('Recurso não encontrado.', 404) })

    const { result } = renderHook(() => useMaterialPage(props))

    expect(result.current.isPrivateAbsence).toBe(true)
    expect(result.current.isRecoverableError).toBe(false)
  })

  it('reports an unavailable response as a recoverable error', () => {
    mockQuery({ error: new RestError('Serviço indisponível.', 503) })

    const { result } = renderHook(() => useMaterialPage(props))

    expect(result.current.isPrivateAbsence).toBe(false)
    expect(result.current.isRecoverableError).toBe(true)
  })

  it('sends a rejected session back to the sign-in route', async () => {
    mockQuery({
      error: new AuthError('authentication-rejected', 'Sua sessão expirou.', {
        statusCode: 401,
      }),
    })

    renderHook(() => useMaterialPage(props))

    await waitFor(() => expect(navigateToMock).toHaveBeenCalledWith('login'))
  })

  it('refetches the material on an explicit retry', async () => {
    const { result } = renderHook(() => useMaterialPage(props))

    await act(async () => {
      await result.current.handleRetry()
    })

    expect(refetchMock).toHaveBeenCalledTimes(1)
  })

  it('opens the recommended Activity inside the current material context', async () => {
    const { result } = renderHook(() => useMaterialPage(props))

    await act(async () => {
      await result.current.handleOpenRecommendation(activityId)
    })

    expect(navigateToActivityMock).toHaveBeenCalledWith(
      props.goalId,
      props.skillId,
      props.competencyId,
      activityId,
    )
    expect(result.current.hasActivityFailure).toBe(false)
    expect(result.current.isOpeningActivity).toBe(false)
  })

  it('keeps a recoverable failure when the Activity cannot be opened', async () => {
    navigateToActivityMock.mockRejectedValue(new Error('navigation failed'))
    const { result } = renderHook(() => useMaterialPage(props))

    await act(async () => {
      await result.current.handleOpenRecommendation(activityId)
    })

    expect(result.current.hasActivityFailure).toBe(true)
    expect(result.current.isOpeningActivity).toBe(false)
  })

  it('clears a previous failure when the Activity is opened again', async () => {
    navigateToActivityMock.mockRejectedValueOnce(new Error('navigation failed'))
    const { result } = renderHook(() => useMaterialPage(props))

    await act(async () => {
      await result.current.handleOpenRecommendation(activityId)
    })
    expect(result.current.hasActivityFailure).toBe(true)

    await act(async () => {
      await result.current.handleOpenRecommendation(activityId)
    })

    expect(result.current.hasActivityFailure).toBe(false)
    expect(navigateToActivityMock).toHaveBeenCalledTimes(2)
  })

  it('exposes the resolved material and no error on the success path', () => {
    mockQuery({ data: detail })

    const { result } = renderHook(() => useMaterialPage(props))

    expect(result.current.detail).toEqual(detail)
    expect(result.current.error).toBeNull()
    expect(result.current.isLoading).toBe(false)
  })

  it('reports the loading state while the query is pending', () => {
    mockQuery({ isPending: true })

    const { result } = renderHook(() => useMaterialPage(props))

    expect(result.current.isLoading).toBe(true)
    expect(result.current.detail).toBeNull()
  })
})
