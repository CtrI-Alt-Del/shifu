import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ROUTES } from '@/constants/routes'
import type { AnchorProps } from '@/ui/shared/widgets/components/anchor'
import { DeletionPanel } from '..'
import { useDeletionPanel } from '../use-deletion-panel'

vi.mock('../use-deletion-panel', () => ({ useDeletionPanel: vi.fn() }))
vi.mock('@/ui/shared/widgets/components/anchor', () => ({
  Anchor: ({ children, route, ...props }: AnchorProps) => (
    <a href={ROUTES[route]} {...props}>
      {typeof children === 'function' ? children({ isActive: false }) : children}
    </a>
  ),
}))
const useDeletionPanelMock = vi.mocked(useDeletionPanel)
function createResult(
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

describe('DeletionPanel', () => {
  afterEach(cleanup)
  beforeEach(() => useDeletionPanelMock.mockReturnValue(createResult()))
  it('explains future closure, unavailable state and privacy destinations', () => {
    const result = createResult()
    useDeletionPanelMock.mockReturnValue(result)
    const { rerender } = render(<DeletionPanel />)
    expect(screen.getByRole('heading', { name: 'Excluir conta' })).toBeVisible()
    expect(screen.getByText(/após o encerramento confirmado/)).toHaveTextContent(
      '24 horas',
    )
    expect(screen.getByText(/ainda não está disponível/)).toBeVisible()
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
    useDeletionPanelMock.mockReturnValue(createResult({ isOpen: true }))
    rerender(<DeletionPanel />)
    expect(screen.getByRole('dialog', { name: 'Excluir sua conta?' })).toBeVisible()
  })
  for (const currentPassword of ['', 'local-secret']) {
    for (const hasConfirmed of [false, true]) {
      it(`keeps deletion disabled with password ${Boolean(currentPassword)} and consent ${hasConfirmed}`, () => {
        useDeletionPanelMock.mockReturnValue(
          createResult({ isOpen: true, currentPassword, hasConfirmed }),
        )
        render(<DeletionPanel />)
        expect(screen.getByLabelText('Senha atual')).toHaveValue(currentPassword)
        expect(screen.getByRole('checkbox')).toHaveProperty('checked', hasConfirmed)
        expect(
          screen.getByRole('button', { name: 'Excluir definitivamente' }),
        ).toBeDisabled()
        expect(screen.queryByRole('form')).not.toBeInTheDocument()
      })
    }
  }
  it('wires input, consent, visibility and cancellation and renders the resulting state', () => {
    const result = createResult({ isOpen: true })
    useDeletionPanelMock.mockReturnValue(result)
    const { rerender } = render(<DeletionPanel />)
    fireEvent.change(screen.getByLabelText('Senha atual'), {
      target: { value: 'local-secret' },
    })
    fireEvent.click(screen.getByRole('checkbox'))
    fireEvent.click(screen.getByRole('button', { name: 'Mostrar senha' }))
    expect(result.handleCurrentPasswordChange).toHaveBeenCalledWith('local-secret')
    expect(result.handleConfirmationChange).toHaveBeenCalledWith(true)
    expect(result.handleTogglePasswordVisibility).toHaveBeenCalledOnce()
    useDeletionPanelMock.mockReturnValue(
      createResult({
        isOpen: true,
        isPasswordVisible: true,
        currentPassword: 'local-secret',
        hasConfirmed: true,
      }),
    )
    rerender(<DeletionPanel />)
    expect(screen.getByLabelText('Senha atual')).toHaveAttribute('type', 'text')
    expect(screen.getByRole('button', { name: 'Ocultar senha' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    useDeletionPanelMock.mockReturnValue(result)
    rerender(<DeletionPanel />)
    fireEvent.click(screen.getByRole('button', { name: 'Fechar confirmação' }))
    expect(result.handleOpenChange).toHaveBeenCalledWith(false)
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(result.handleOpenChange).toHaveBeenCalledWith(false)
    useDeletionPanelMock.mockReturnValue(createResult())
    rerender(<DeletionPanel />)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})
