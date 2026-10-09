import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { RemoveSessionDialog } from '..'
import { useRemoveSessionDialog } from '../use-remove-session-dialog'

vi.mock('../use-remove-session-dialog', () => ({ useRemoveSessionDialog: vi.fn() }))
const useRemoveSessionDialogMock = vi.mocked(useRemoveSessionDialog)
const closeDialogMock = vi.fn()
const removeSessionMock = vi.fn()

describe('RemoveSessionDialog', () => {
  afterEach(cleanup)

  it('requires explicit confirmation and keeps the action available for retry after failure', () => {
    useRemoveSessionDialogMock.mockReturnValue({
      activeDialog: 'remove',
      closeDialog: closeDialogMock,
      isRemovingSession: false,
      removalError: 'Não foi possível excluir a conversa.',
      removeSession: removeSessionMock,
      session: { id: 'session-1', title: 'Conversa de estudo' },
    } as unknown as ReturnType<typeof useRemoveSessionDialog>)
    render(<RemoveSessionDialog />)
    expect(screen.getByRole('alertdialog', { name: 'Excluir conversa?' })).toBeVisible()
    expect(screen.getByText('Conversa de estudo')).toBeVisible()
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Não foi possível excluir a conversa.',
    )
    fireEvent.click(screen.getByRole('button', { name: 'Manter conversa' }))
    expect(closeDialogMock).toHaveBeenCalledOnce()
    fireEvent.click(screen.getByRole('button', { name: 'Excluir conversa' }))
    expect(removeSessionMock).toHaveBeenCalledOnce()
  })
})
