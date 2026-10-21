import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { RenameSessionDialog } from '..'
import { useRenameSessionDialog } from '../use-rename-session-dialog'

vi.mock('../use-rename-session-dialog', () => ({ useRenameSessionDialog: vi.fn() }))
const useRenameSessionDialogMock = vi.mocked(useRenameSessionDialog)
const closeDialogMock = vi.fn()

describe('RenameSessionDialog', () => {
  afterEach(cleanup)

  it('shows the current title and preserves it when rename fails', () => {
    useRenameSessionDialogMock.mockReturnValue({
      activeDialog: 'rename',
      closeDialog: closeDialogMock,
      handleSubmit: vi.fn(),
      isRenamingSession: false,
      renameError: 'Não foi possível renomear.',
      session: { id: 'session-1', title: 'Título atual' },
      setTitle: vi.fn(),
      title: 'Título atual',
      validationError: null,
    } as unknown as ReturnType<typeof useRenameSessionDialog>)
    render(<RenameSessionDialog />)
    expect(screen.getByLabelText('Título da conversa')).toHaveValue('Título atual')
    expect(screen.getByRole('alert')).toHaveTextContent('Não foi possível renomear.')
    expect(screen.getByRole('button', { name: 'Salvar' })).toBeEnabled()
    fireEvent.change(screen.getByLabelText('Título da conversa'), {
      target: { value: 'Título alterado' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Fechar' }))
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(closeDialogMock).toHaveBeenCalled()
  })

  it('submits a valid rename and disables changes while saving', () => {
    const handleSubmit = vi.fn((event: React.FormEvent<HTMLFormElement>) =>
      event.preventDefault(),
    )
    useRenameSessionDialogMock.mockReturnValue({
      activeDialog: 'rename',
      closeDialog: closeDialogMock,
      handleSubmit,
      isRenamingSession: true,
      renameError: null,
      session: { id: 'session-1', title: 'Título atual' },
      setTitle: vi.fn(),
      title: 'Título novo',
      validationError: 'Título obrigatório.',
    } as unknown as ReturnType<typeof useRenameSessionDialog>)
    render(<RenameSessionDialog />)
    expect(screen.getByRole('alert')).toHaveTextContent('Título obrigatório.')
    expect(screen.getByRole('button', { name: 'Salvando…' })).toBeDisabled()
    fireEvent.submit(
      screen.getByLabelText('Título da conversa').closest('form') as HTMLFormElement,
    )
    expect(handleSubmit).toHaveBeenCalledOnce()
  })
})
