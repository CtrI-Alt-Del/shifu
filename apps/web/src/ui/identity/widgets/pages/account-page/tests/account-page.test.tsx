import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthError } from '@/core/errors/auth-error'
import { ROUTES } from '@/constants/routes'
import type { AnchorProps } from '@/ui/shared/widgets/components/anchor'
import { AccountPage } from '..'
import { useAccountPage } from '../use-account-page'
vi.mock('../use-account-page', () => ({ useAccountPage: vi.fn() }))
vi.mock('@/ui/shared/contexts/auth-context/use-auth-context', () => ({
  useAuthContext: () => ({
    updateAccountProfile: vi.fn(),
    changeAccountPassword: vi.fn(),
  }),
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
const useAccountPageMock = vi.mocked(useAccountPage)
function createResult(
  overrides: Partial<ReturnType<typeof useAccountPage>> = {},
): ReturnType<typeof useAccountPage> {
  return {
    activeTab: 'profile',
    accountProfile: {
      accountId: 'a',
      displayName: 'Maria',
      email: 'm@example.com',
      timeZone: 'UTC',
    },
    isLoadingAccountProfile: false,
    accountProfileError: null,
    handleTabChange: vi.fn(),
    refetchAccountProfile: vi.fn(),
    ...overrides,
  }
}
function renderPage() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <AccountPage accountEmail='m@example.com' />
    </QueryClientProvider>,
  )
}
describe('AccountPage', () => {
  afterEach(cleanup)
  beforeEach(() => {
    useAccountPageMock.mockReturnValue(createResult())
    window.matchMedia = vi.fn().mockReturnValue({
      matches: true,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })
  })
  it('renders the real profile form and canonical privacy destinations', () => {
    renderPage()
    expect(screen.getByRole('heading', { name: 'Sua conta' })).toBeVisible()
    expect(screen.getByLabelText('Nome de exibição')).toHaveValue('Maria')
    expect(
      screen.getByRole('link', { name: 'Consultar política de privacidade' }),
    ).toHaveAttribute('href', ROUTES.privacy)
    expect(screen.getByRole('link', { name: 'Solicitar atendimento' })).toHaveAttribute(
      'href',
      expect.stringContaining('mailto:shifu.ctrlaltdel@gmail.com'),
    )
    expect(screen.queryByRole('tab', { name: 'Excluir conta' })).not.toBeInTheDocument()
    expect(screen.getByLabelText('Senha atual')).not.toBeVisible()
  })
  it('shows skeleton and recoverable query failures', () => {
    useAccountPageMock.mockReturnValue(
      createResult({ isLoadingAccountProfile: true, accountProfile: null }),
    )
    const { unmount } = renderPage()
    expect(screen.getByRole('status')).toHaveAccessibleName('Carregando sua conta')
    expect(screen.getByRole('heading', { name: 'Sua conta' })).toBeVisible()
    unmount()
    const refetchAccountProfileMock = vi.fn()
    useAccountPageMock.mockReturnValue(
      createResult({
        accountProfile: null,
        accountProfileError: new AuthError('unavailable', 'Tente novamente.'),
        refetchAccountProfile: refetchAccountProfileMock,
      }),
    )
    renderPage()
    expect(screen.getByRole('alert')).toHaveTextContent('Tente novamente.')
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    expect(refetchAccountProfileMock).toHaveBeenCalledOnce()
  })
  it('renders real security composition and hides inactive profile controls', () => {
    useAccountPageMock.mockReturnValue(createResult({ activeTab: 'security' }))
    renderPage()
    expect(screen.getByLabelText('Senha atual')).toBeVisible()
    expect(screen.getByLabelText('Nome de exibição')).not.toBeVisible()
    expect(screen.getByRole('tab', { name: 'Segurança' })).toHaveAttribute(
      'aria-selected',
      'true',
    )
  })
})
