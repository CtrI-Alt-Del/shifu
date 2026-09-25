import { act, fireEvent, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useAuthContext } from '@/ui/shared/contexts/auth-context/use-auth-context'
import { useNavigation } from '@/ui/shared/hooks/use-navigation'

import { useAccountMenu } from '../use-account-menu'

vi.mock('@/ui/shared/contexts/auth-context/use-auth-context', () => ({
  useAuthContext: vi.fn(),
}))
vi.mock('@/ui/shared/hooks/use-navigation', () => ({
  useNavigation: vi.fn(),
}))

const useAuthContextMock = vi.mocked(useAuthContext)
const useNavigationMock = vi.mocked(useNavigation)
const signOutMock = vi.fn()
const navigateToMock = vi.fn()

describe('useAccountMenu', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    signOutMock.mockResolvedValue(undefined)
    navigateToMock.mockResolvedValue(undefined)
    useAuthContextMock.mockReturnValue({
      confirmEmail: vi.fn(),
      exitPendingConfirmation: vi.fn(),
      getPendingConfirmationStatus: vi.fn(),
      registerAccount: vi.fn(),
      resendConfirmation: vi.fn(),
      signIn: vi.fn(),
      signOut: signOutMock,
    })
    useNavigationMock.mockReturnValue({
      navigateTo: navigateToMock,
      navigateToGoalDetail: vi.fn(),
      navigateToActivity: vi.fn(),
      navigateToPlanner: vi.fn(),
    })
  })

  it('opens, dismisses on Escape and restores focus to the trigger', () => {
    const { result } = renderHook(() => useAccountMenu())
    const trigger = document.createElement('button')
    trigger.id = result.current.triggerId
    document.body.append(trigger)
    const menu = document.createElement('div')
    result.current.menuRef.current = menu

    act(() => result.current.handleToggle())
    expect(result.current.isOpen).toBe(true)

    trigger.focus()
    fireEvent.keyDown(document, { key: 'Escape' })

    expect(result.current.isOpen).toBe(false)
    expect(trigger).toHaveFocus()
    trigger.remove()
  })

  it('closes on outside pointer interaction but ignores pointers inside the menu', () => {
    const { result } = renderHook(() => useAccountMenu())
    const menu = document.createElement('div')
    const child = document.createElement('button')
    menu.append(child)
    document.body.append(menu)
    result.current.menuRef.current = menu

    act(() => result.current.handleToggle())
    fireEvent.pointerDown(child)
    expect(result.current.isOpen).toBe(true)

    fireEvent.pointerDown(document.body)
    expect(result.current.isOpen).toBe(false)
    menu.remove()
  })

  it('prevents duplicate logout requests and navigates after success', async () => {
    let resolveSignOut: () => void = () => undefined
    signOutMock.mockImplementation(
      () =>
        new Promise<void>((resolve) => {
          resolveSignOut = resolve
        }),
    )
    const { result } = renderHook(() => useAccountMenu())

    act(() => {
      void result.current.handleSignOut()
      void result.current.handleSignOut()
    })

    expect(result.current.status).toBe('pending')
    expect(signOutMock).toHaveBeenCalledOnce()

    await act(async () => {
      resolveSignOut()
      await waitFor(() => expect(navigateToMock).toHaveBeenCalledWith('login'))
    })

    expect(result.current.status).toBe('success')
  })

  it('keeps the menu recoverable after a safe logout failure', async () => {
    signOutMock.mockRejectedValueOnce(new Error('provider details'))
    const { result } = renderHook(() => useAccountMenu())

    await act(async () => {
      await result.current.handleSignOut()
    })

    expect(result.current.status).toBe('error')
    expect(result.current.errorMessage).toBe(
      'Não foi possível sair agora. Tente novamente.',
    )
    expect(navigateToMock).not.toHaveBeenCalled()

    await act(async () => {
      await result.current.handleSignOut()
    })

    expect(signOutMock).toHaveBeenCalledTimes(2)
    expect(navigateToMock).toHaveBeenCalledWith('login')
  })
})
