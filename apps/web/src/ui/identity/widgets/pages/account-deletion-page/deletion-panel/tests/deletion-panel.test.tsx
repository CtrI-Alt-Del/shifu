import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ROUTES } from '@/constants/routes'
import type { AnchorProps } from '@/ui/shared/widgets/components/anchor'
import { DeletionPanel } from '..'
import { useDeletionPanel } from '../use-deletion-panel'
import { useDeleteAccountAction } from '../use-delete-account-action'

vi.mock('../use-deletion-panel', () => ({ useDeletionPanel: vi.fn() }))
vi.mock('../use-delete-account-action', () => ({ useDeleteAccountAction: vi.fn() }))
vi.mock('@/ui/shared/widgets/components/anchor', () => ({
  Anchor: ({ children, route, ...props }: AnchorProps) => (
    <a href={ROUTES[route]} {...props}>
      {typeof children === 'function' ? children({ isActive: false }) : children}
    </a>
  ),
}))

const useDeletionPanelMock = vi.mocked(useDeletionPanel)
const useDeleteAccountActionMock = vi.mocked(useDeleteAccountAction)

function createPanelResult(
  overrides: Partial<ReturnType<typeof useDeletionPanel>> = {},
): ReturnType<typeof useDeletionPanel> {
  return {
    isOpen: false,
    currentPassword: '',
    hasConfirmed: false,
    isPasswordVisible: false,
    handleOpenChange: vi.fn(),
    handleCurrentPasswordChange: vi.fn(),
    handleConfirmationChange: vi.fn(),
    handleTogglePasswordVisibility: vi.fn(),
    ...overrides,
  }
}

function createActionResult(
  overrides: Partial<ReturnType<typeof useDeleteAccountAction>> = {},
): ReturnType<typeof useDeleteAccountAction> {
  return {
    canCheckStatus: false,
    errorMessage: null,
    isPasswordInvalid: false,
    isCheckingStatus: false,
    isSubmitting: false,
    clearFeedback: vi.fn(),
    checkStatus: vi.fn(),
    submit: vi.fn(),
    ...overrides,
  }
}

describe('DeletionPanel', () => {
  afterEach(cleanup)
  beforeEach(() => {
    useDeletionPanelMock.mockReturnValue(createPanelResult())
    useDeleteAccountActionMock.mockReturnValue(createActionResult())
  })

  it('explains definitive closure, the offline browser exception and privacy destinations', () => {
    const result = createPanelResult()
    useDeletionPanelMock.mockReturnValue(result)
    const { rerender } = render(<DeletionPanel />)

    expect(screen.getByRole('heading', { name: 'Excluir conta' })).toBeVisible()
    expect(screen.getByText(/o acesso é bloqueado imediatamente/)).toHaveTextContent(
      '24 horas',
    )
    expect(screen.getByText(/navegador desconectado/)).toBeVisible()
    expect(screen.getByRole('link', { name: 'Política de privacidade' })).toHaveAttribute(
      'href',
      ROUTES.privacy,
    )
    expect(screen.getByRole('link', { name: 'Solicitar atendimento' })).toHaveAttribute(
      'href',
      expect.stringContaining('mailto:'),
    )

    fireEvent.click(screen.getByRole('button', { name: 'Excluir minha conta' }))
    expect(result.handleOpenChange).toHaveBeenCalledWith(true)
    useDeletionPanelMock.mockReturnValue(createPanelResult({ isOpen: true }))
    rerender(<DeletionPanel />)
    expect(screen.getByRole('dialog', { name: 'Excluir sua conta?' })).toBeVisible()
    expect(screen.getByRole('button', { name: 'Excluir definitivamente' })).toBeDisabled()
  })

  for (const currentPassword of ['', 'local-secret']) {
    for (const hasConfirmed of [false, true]) {
      it(`requires password ${Boolean(currentPassword)} and consent ${hasConfirmed}`, () => {
        useDeletionPanelMock.mockReturnValue(
          createPanelResult({ isOpen: true, currentPassword, hasConfirmed }),
        )
        render(<DeletionPanel />)
        expect(screen.getByLabelText('Senha atual')).toHaveValue(currentPassword)
        expect(screen.getByRole('checkbox')).toHaveProperty('checked', hasConfirmed)
        const finalButton = screen.getByRole('button', {
          name: 'Excluir definitivamente',
        })
        if (!currentPassword || !hasConfirmed) expect(finalButton).toBeDisabled()
        else expect(finalButton).toBeEnabled()
      })
    }
  }

  it('submits only after password and explicit confirmation, and clears on cancel', () => {
    const result = createPanelResult({
      isOpen: true,
      currentPassword: 'local-secret',
      hasConfirmed: true,
    })
    const action = createActionResult()
    useDeletionPanelMock.mockReturnValue(result)
    useDeleteAccountActionMock.mockReturnValue(action)
    const { rerender } = render(<DeletionPanel />)

    fireEvent.click(screen.getByRole('button', { name: 'Excluir definitivamente' }))
    expect(action.submit).toHaveBeenCalledWith('local-secret')

    fireEvent.click(screen.getByRole('button', { name: 'Mostrar senha' }))
    expect(result.handleTogglePasswordVisibility).toHaveBeenCalledOnce()
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(result.handleOpenChange).toHaveBeenCalledWith(false)

    useDeletionPanelMock.mockReturnValue(createPanelResult())
    rerender(<DeletionPanel />)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('clears stale feedback when the dialog opens again', () => {
    const panel = createPanelResult()
    const action = createActionResult({
      canCheckStatus: true,
      errorMessage: 'A senha atual está incorreta.',
      isPasswordInvalid: true,
    })
    useDeletionPanelMock.mockReturnValue(panel)
    useDeleteAccountActionMock.mockReturnValue(action)
    const { rerender } = render(<DeletionPanel />)

    fireEvent.click(screen.getByRole('button', { name: 'Excluir minha conta' }))
    expect(panel.handleOpenChange).toHaveBeenCalledWith(true)
    expect(action.clearFeedback).toHaveBeenCalledOnce()

    useDeletionPanelMock.mockReturnValue(createPanelResult({ isOpen: true }))
    useDeleteAccountActionMock.mockReturnValue(createActionResult())
    rerender(<DeletionPanel />)
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: 'Verificar estado' }),
    ).not.toBeInTheDocument()
  })

  it('announces errors and offers status recovery without claiming closure', () => {
    useDeletionPanelMock.mockReturnValue(createPanelResult({ isOpen: true }))
    useDeleteAccountActionMock.mockReturnValue(
      createActionResult({
        canCheckStatus: true,
        errorMessage:
          'Não foi possível confirmar o estado. Uma falha de conexão não confirma o encerramento.',
        isCheckingStatus: false,
      }),
    )
    render(<DeletionPanel />)

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Uma falha de conexão não confirma o encerramento.',
    )
    const checkStatus = screen.getByRole('button', { name: 'Verificar estado' })
    fireEvent.click(checkStatus)
    expect(
      useDeleteAccountActionMock.mock.results.at(-1)?.value.checkStatus,
    ).toBeDefined()
  })

  it('disables every close action while a request is pending', () => {
    useDeletionPanelMock.mockReturnValue(createPanelResult({ isOpen: true }))
    useDeleteAccountActionMock.mockReturnValue(createActionResult({ isSubmitting: true }))
    render(<DeletionPanel />)

    expect(screen.getByRole('button', { name: 'Cancelar' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Fechar confirmação' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Encerrando conta…' })).toBeDisabled()
  })
})
