import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { AccountMenu } from '..'
import { useAccountMenu } from '../use-account-menu'

vi.mock('../use-account-menu', () => ({
  useAccountMenu: vi.fn(),
}))

const useAccountMenuMock = vi.mocked(useAccountMenu)
const handleSignOutMock = vi.fn()
const handleToggleMock = vi.fn()

type AccountMenuController = ReturnType<typeof useAccountMenu>

function createController(
  overrides: Partial<AccountMenuController> = {},
): AccountMenuController {
  return {
    alertRef: { current: null },
    errorMessage: null,
    handleSignOut: handleSignOutMock,
    handleToggle: handleToggleMock,
    isOpen: false,
    menuId: 'account-menu-test',
    menuRef: { current: null },
    status: 'idle',
    triggerId: 'account-menu-trigger-test',
    ...overrides,
  }
}

describe('AccountMenu', () => {
  afterEach(cleanup)

  beforeEach(() => {
    vi.clearAllMocks()
    useAccountMenuMock.mockReturnValue(createController())
  })

  it('renders the account summary and keeps only Sair enabled', () => {
    useAccountMenuMock.mockReturnValue(createController({ isOpen: true }))

    render(
      <AccountMenu account={{ displayName: 'Thiago', email: 'thiago@exemplo.com' }} />,
    )

    expect(screen.getByRole('button', { name: 'Fechar menu da conta' })).toHaveAttribute(
      'aria-expanded',
      'true',
    )
    expect(screen.getByText('Thiago')).toBeVisible()
    expect(screen.getByText('thiago@exemplo.com')).toBeVisible()

    const accountItem = screen.getByRole('menuitem', { name: 'Sua conta' })
    expect(accountItem).toBeDisabled()
    expect(accountItem).toHaveAttribute('aria-disabled', 'true')
    expect(accountItem).toHaveAttribute('tabindex', '-1')
    expect(screen.getByRole('menuitem', { name: 'Sair' })).toBeEnabled()
  })

  it('delegates trigger and logout actions through the owning hook', () => {
    useAccountMenuMock.mockReturnValue(createController({ isOpen: true }))
    render(
      <AccountMenu account={{ displayName: 'Thiago', email: 'thiago@exemplo.com' }} />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Fechar menu da conta' }))
    fireEvent.click(screen.getByRole('menuitem', { name: 'Sair' }))

    expect(handleToggleMock).toHaveBeenCalledOnce()
    expect(handleSignOutMock).toHaveBeenCalledOnce()
  })

  it('shows announced pending, recoverable failure and success states', () => {
    useAccountMenuMock.mockReturnValue(
      createController({ isOpen: true, status: 'pending' }),
    )
    const { rerender } = render(
      <AccountMenu account={{ displayName: 'Thiago', email: 'thiago@exemplo.com' }} />,
    )

    expect(screen.getByRole('menuitem', { name: 'Saindo...' })).toBeDisabled()
    expect(screen.getByRole('menuitem', { name: 'Saindo...' })).toHaveAttribute(
      'aria-busy',
      'true',
    )

    useAccountMenuMock.mockReturnValue(
      createController({
        errorMessage: 'Não foi possível sair agora. Tente novamente.',
        isOpen: true,
        status: 'error',
      }),
    )
    rerender(
      <AccountMenu account={{ displayName: 'Thiago', email: 'thiago@exemplo.com' }} />,
    )
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Pressione Sair para tentar novamente.',
    )
    expect(screen.getByRole('menuitem', { name: 'Sair' })).toBeEnabled()

    useAccountMenuMock.mockReturnValue(
      createController({ isOpen: true, status: 'success' }),
    )
    rerender(
      <AccountMenu account={{ displayName: 'Thiago', email: 'thiago@exemplo.com' }} />,
    )
    expect(screen.getByRole('status')).toHaveTextContent(
      'Saída concluída. Redirecionando para Entrar...',
    )
    expect(screen.queryByRole('menuitem', { name: 'Sair' })).not.toBeInTheDocument()
  })
})
