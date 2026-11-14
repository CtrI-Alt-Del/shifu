import { createElement, type PropsWithChildren } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthError } from '@/core/errors/auth-error'
import type { ProfileFormProps } from '..'
import { useProfileForm } from '../use-profile-form'
import { useUpdateAccountProfileAction } from '../use-update-account-profile-action'
vi.mock('../use-update-account-profile-action', () => ({
  useUpdateAccountProfileAction: vi.fn(),
}))

const { canonicalUpdateMock, refreshRouteMock } = vi.hoisted(() => ({
  canonicalUpdateMock: vi.fn(),
  refreshRouteMock: vi.fn(),
}))
vi.mock('@/ui/shared/contexts/auth-context/use-auth-context', () => ({
  useAuthContext: () => ({ updateAccountProfile: canonicalUpdateMock }),
}))
vi.mock('@/ui/shared/hooks/use-navigation', () => ({
  useNavigation: () => ({ refreshCurrentRoute: refreshRouteMock }),
}))

const useUpdateAccountProfileActionMock = vi.mocked(useUpdateAccountProfileAction)
const updateAccountProfileMock = vi.fn()
const PROFILE = {
  accountId: 'account-a',
  displayName: 'Maria',
  email: 'maria@example.com',
  timeZone: 'UTC',
}
const EVENT = {
  preventDefault: vi.fn(),
  stopPropagation: vi.fn(),
} as unknown as React.FormEvent<HTMLFormElement>
describe('useProfileForm', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useUpdateAccountProfileActionMock.mockReset()
    updateAccountProfileMock.mockResolvedValue(PROFILE)
    useUpdateAccountProfileActionMock.mockReturnValue({
      isPending: false,
      error: null,
      refreshWarning: null,
      updateAccountProfile: updateAccountProfileMock,
    })
  })
  it('uses saved data and preserves a dirty draft across refetch', () => {
    const { result, rerender } = renderHook(
      (props: ProfileFormProps) => useProfileForm(props),
      { initialProps: { profile: PROFILE } },
    )
    expect(result.current.email).toBe(PROFILE.email)
    expect(result.current.timeZone).toBe('UTC')
    expect(result.current.isSuggestedTimeZone).toBe(false)
    act(() => result.current.handleDisplayNameChange('Draft'))
    rerender({ profile: { ...PROFILE, displayName: 'Remote' } })
    expect(result.current.displayName).toBe('Draft')
    act(() => result.current.handleTimeZoneChange('America/Sao_Paulo'))
    expect(result.current.timeZone).toBe('America/Sao_Paulo')
    expect(
      result.current.timeZoneOptions.find((option) => option.value === 'UTC')?.label,
    ).toContain('Tempo universal')
  })
  it('suggests without submitting and rejects an empty selection and blank name', async () => {
    const { result } = renderHook(() =>
      useProfileForm({ profile: { ...PROFILE, timeZone: null } }),
    )
    expect(result.current.isSuggestedTimeZone).toBe(true)
    expect(updateAccountProfileMock).not.toHaveBeenCalled()
    act(() => {
      result.current.handleTimeZoneChange(null)
      result.current.handleDisplayNameChange('   ')
    })
    await act(async () => result.current.handleSubmit(EVENT))
    expect(result.current.errors.displayName).toBeDefined()
    expect(result.current.errors.timeZone).toBeDefined()
    expect(result.current.message).toBe('Revise os campos destacados.')
    expect(updateAccountProfileMock).not.toHaveBeenCalled()
  })
  it.each(['missing', 'throws'] as const)(
    'requires explicit timezone selection when browser detection %s',
    async (failure) => {
      const originalOptions = new Intl.DateTimeFormat().resolvedOptions()
      const resolvedOptionsMock = vi
        .spyOn(Intl.DateTimeFormat.prototype, 'resolvedOptions')
        .mockImplementation(() => {
          if (failure === 'throws') throw new Error('Timezone detection unavailable')
          return { ...originalOptions, timeZone: '' }
        })
      try {
        const { result } = renderHook(() =>
          useProfileForm({ profile: { ...PROFILE, timeZone: null } }),
        )
        expect(result.current.timeZone).toBe('')
        expect(result.current.isSuggestedTimeZone).toBe(false)
        expect(updateAccountProfileMock).not.toHaveBeenCalled()
        await act(async () => result.current.handleSubmit(EVENT))
        expect(result.current.errors.timeZone).toBeDefined()
        expect(updateAccountProfileMock).not.toHaveBeenCalled()
        act(() => result.current.handleTimeZoneChange('UTC'))
        expect(result.current.timeZone).toBe('UTC')
        expect(result.current.isSuggestedTimeZone).toBe(false)
        expect(updateAccountProfileMock).not.toHaveBeenCalled()
        await act(async () => result.current.handleSubmit(EVENT))
        expect(updateAccountProfileMock).toHaveBeenCalledOnce()
        expect(updateAccountProfileMock).toHaveBeenCalledWith({
          displayName: PROFILE.displayName,
          timeZone: 'UTC',
        })
        expect(result.current.isSuccess).toBe(true)
      } finally {
        resolvedOptionsMock.mockRestore()
      }
    },
  )
  it('normalizes a valid save and adopts its canonical result', async () => {
    const { result } = renderHook(() => useProfileForm({ profile: PROFILE }))
    act(() => result.current.handleDisplayNameChange('  Maria  '))
    await act(async () => result.current.handleSubmit(EVENT))
    expect(updateAccountProfileMock).toHaveBeenCalledWith({
      displayName: 'Maria',
      timeZone: 'UTC',
    })
    expect(result.current.isSuccess).toBe(true)
    expect(result.current.message).toBe('Perfil salvo.')
    expect(result.current.displayName).toBe('Maria')
  })
  it('retains drafts and exposes server field failure for recovery', async () => {
    updateAccountProfileMock.mockRejectedValue(
      new AuthError('validation-failed', 'Fuso inválido.', { field: 'timeZone' }),
    )
    const { result } = renderHook(() => useProfileForm({ profile: PROFILE }))
    act(() => result.current.handleDisplayNameChange('Draft'))
    await act(async () => result.current.handleSubmit(EVENT))
    expect(result.current.errors.timeZone).toBe('Fuso inválido.')
    expect(result.current.displayName).toBe('Draft')
    expect(result.current.isSuccess).toBe(false)
    updateAccountProfileMock.mockResolvedValue({ ...PROFILE, displayName: 'Draft' })
    await act(async () => result.current.handleSubmit(EVENT))
    expect(result.current.isSuccess).toBe(true)
  })
  it('guards duplicate submissions and exposes pending and refresh warnings', async () => {
    let resolveSave: (value: typeof PROFILE) => void = () => undefined
    updateAccountProfileMock.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveSave = resolve
        }),
    )
    const { result } = renderHook(() => useProfileForm({ profile: PROFILE }))
    act(() => {
      void result.current.handleSubmit(EVENT)
      void result.current.handleSubmit(EVENT)
    })
    await waitFor(() => expect(updateAccountProfileMock).toHaveBeenCalledOnce())
    await act(async () => resolveSave(PROFILE))
    expect(result.current.message).toBe('Perfil salvo.')
  })
  it('exposes pending and confirmed-save refresh warning without reporting a save failure', () => {
    useUpdateAccountProfileActionMock.mockReturnValue({
      isPending: true,
      error: null,
      refreshWarning: 'Perfil salvo. Atualize o menu.',
      updateAccountProfile: updateAccountProfileMock,
    })
    const { result } = renderHook(() => useProfileForm({ profile: PROFILE }))
    expect(result.current.isPending).toBe(true)
    expect(result.current.refreshWarning).toBe('Perfil salvo. Atualize o menu.')
  })
  it('keeps a canonical save successful when refreshing route identity fails', async () => {
    const { useUpdateAccountProfileAction: useRealAction } = await vi.importActual<
      typeof import('../use-update-account-profile-action')
    >('../use-update-account-profile-action')
    useUpdateAccountProfileActionMock.mockImplementation(useRealAction)
    canonicalUpdateMock.mockResolvedValue({ ...PROFILE, displayName: 'Ana' })
    refreshRouteMock.mockRejectedValue(new Error('route unavailable'))
    const queryClient = new QueryClient()
    function QueryWrapper({ children }: PropsWithChildren) {
      return createElement(QueryClientProvider, { client: queryClient }, children)
    }
    const { result } = renderHook(() => useProfileForm({ profile: PROFILE }), {
      wrapper: QueryWrapper,
    })
    act(() => result.current.handleDisplayNameChange('Ana'))
    await act(async () => result.current.handleSubmit(EVENT))
    expect(result.current.isSuccess).toBe(true)
    expect(result.current.message).toBe('Perfil salvo.')
    expect(result.current.refreshWarning).toContain('Perfil salvo.')
    expect(result.current.displayName).toBe('Ana')
    expect(
      queryClient.getQueryData(['identity', 'account-profile', PROFILE.email]),
    ).toEqual({ ...PROFILE, displayName: 'Ana' })
    expect(canonicalUpdateMock).toHaveBeenCalledOnce()
    queryClient.clear()
  })
  it.each([1, 160, 161])('enforces the name boundary at %i characters', async (count) => {
    const { result } = renderHook(() => useProfileForm({ profile: PROFILE }))
    act(() => result.current.handleDisplayNameChange('a'.repeat(count)))
    await act(async () => result.current.handleSubmit(EVENT))
    expect(updateAccountProfileMock).toHaveBeenCalledTimes(count <= 160 ? 1 : 0)
  })
})
