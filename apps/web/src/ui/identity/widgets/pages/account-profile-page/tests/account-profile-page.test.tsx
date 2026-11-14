import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthError } from '@/core/errors/auth-error'
import { ROUTES } from '@/constants/routes'
import type { AnchorProps } from '@/ui/shared/widgets/components/anchor'
import { AccountProfilePage } from '..'
import { useAccountProfilePage } from '../use-account-profile-page'
vi.mock('../use-account-profile-page', () => ({ useAccountProfilePage: vi.fn() }))
vi.mock('@/ui/shared/contexts/auth-context/use-auth-context', () => ({
  useAuthContext: () => ({ updateAccountProfile: vi.fn() }),
}))
vi.mock('@/ui/shared/hooks/use-navigation', () => ({
  useNavigation: () => ({ refreshCurrentRoute: vi.fn() }),
}))
vi.mock('@/ui/shared/hooks/use-reduced-motion-preference', () => ({
  useReducedMotionPreference: () => ({ prefersReducedMotion: true }),
}))
vi.mock('@/ui/shared/widgets/components/anchor', () => ({
  Anchor: ({ children, route, ...props }: AnchorProps) => (
    <a href={ROUTES[route]} {...props}>
      {typeof children === 'function' ? children({ isActive: false }) : children}
    </a>
  ),
}))
const useAccountProfilePageMock = vi.mocked(useAccountProfilePage)
function createResult(
  overrides: Partial<ReturnType<typeof useAccountProfilePage>> = {},
): ReturnType<typeof useAccountProfilePage> {
  return {
    accountProfile: {
      accountId: 'a',
      displayName: 'Maria',
      email: 'm@example.com',
      timeZone: 'UTC',
    },
    isLoadingAccountProfile: false,
    accountProfileError: null,
    refetchAccountProfile: vi.fn(),
    ...overrides,
  }
}
function renderPage() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <AccountProfilePage accountEmail='m@example.com' />
    </QueryClientProvider>,
  )
}
describe('AccountProfilePage', () => {
  afterEach(cleanup)
  beforeEach(() => {
    useAccountProfilePageMock.mockReturnValue(createResult())
    window.matchMedia = vi.fn().mockReturnValue({
      matches: true,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })
  })
  it('renders the real profile form and canonical privacy destinations', () => {
    renderPage()
    expect(useAccountProfilePageMock).toHaveBeenCalledWith({
      accountEmail: 'm@example.com',
    })
    expect(screen.getByLabelText('Nome de exibição')).toHaveValue('Maria')
    expect(
      screen.getByRole('link', { name: 'Consultar política de privacidade' }),
    ).toHaveAttribute('href', ROUTES.privacy)
    expect(screen.getByRole('link', { name: 'Solicitar atendimento' })).toHaveAttribute(
      'href',
      expect.stringContaining('mailto:shifu.ctrlaltdel@gmail.com'),
    )
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
  it('shows the skeleton while the profile loads', () => {
    useAccountProfilePageMock.mockReturnValue(
      createResult({ isLoadingAccountProfile: true, accountProfile: null }),
    )
    renderPage()
    expect(screen.getByRole('status')).toHaveAccessibleName('Carregando sua conta')
    expect(screen.queryByLabelText('Nome de exibição')).not.toBeInTheDocument()
  })
  it('shows a recoverable failure without inventing a profile', () => {
    const refetchAccountProfileMock = vi.fn()
    useAccountProfilePageMock.mockReturnValue(
      createResult({
        accountProfile: null,
        accountProfileError: new AuthError('unavailable', 'Tente novamente.'),
        refetchAccountProfile: refetchAccountProfileMock,
      }),
    )
    renderPage()
    expect(screen.getByRole('alert')).toHaveTextContent('Tente novamente.')
    expect(screen.queryByLabelText('Nome de exibição')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    expect(refetchAccountProfileMock).toHaveBeenCalledOnce()
  })
  it('keeps the loaded form and announces a failed refresh beside it', () => {
    const refetchAccountProfileMock = vi.fn()
    useAccountProfilePageMock.mockReturnValue(
      createResult({
        accountProfileError: new AuthError('unavailable', 'Indisponível.'),
        refetchAccountProfile: refetchAccountProfileMock,
      }),
    )
    renderPage()
    expect(screen.getByRole('alert')).toHaveTextContent('Seu rascunho foi mantido.')
    expect(screen.getByLabelText('Nome de exibição')).toHaveValue('Maria')
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    expect(refetchAccountProfileMock).toHaveBeenCalledOnce()
  })
})
