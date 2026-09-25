import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'

import { ConfirmationDialog } from '../index'

describe('ConfirmationDialog', () => {
  it('renders nothing when isOpen is false', () => {
    const { container } = render(
      <ConfirmationDialog
        title='Delete Item'
        description='This action cannot be undone'
        confirmLabel='Delete'
        cancelLabel='Cancel'
        icon='trash-2'
        isOpen={false}
        isSubmitting={false}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    )

    expect(container.querySelector('[role="alertdialog"]')).not.toBeInTheDocument()
  })

  it('renders the destructive scope copy without a confirmation input', () => {
    render(
      <ConfirmationDialog
        title='Remove Goal'
        description='All Habilidade experiences will be removed permanently'
        confirmLabel='Remove'
        cancelLabel='Cancel'
        icon='trash-2'
        isOpen={true}
        isSubmitting={false}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    )

    expect(screen.getByText('Remove Goal')).toBeInTheDocument()
    expect(
      screen.getByText('All Habilidade experiences will be removed permanently'),
    ).toBeInTheDocument()
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
  })

  it('renders the item name when provided', () => {
    render(
      <ConfirmationDialog
        title='Remove Goal'
        itemName='Automatizar tarefas do dia a dia com Python'
        description='All Habilidade experiences will be removed permanently'
        confirmLabel='Remove'
        cancelLabel='Cancel'
        icon='trash-2'
        isOpen={true}
        isSubmitting={false}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    )

    expect(
      screen.getByText('Automatizar tarefas do dia a dia com Python'),
    ).toBeInTheDocument()
  })

  it('disables both actions while isSubmitting', () => {
    render(
      <ConfirmationDialog
        title='Confirm'
        description='Are you sure?'
        confirmLabel='Yes'
        cancelLabel='No'
        icon='trash-2'
        isOpen={true}
        isSubmitting={true}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    )

    const buttons = screen.getAllByRole('button')
    buttons.forEach((btn) => {
      expect(btn).toBeDisabled()
    })
  })

  it('renders the error message when provided', () => {
    render(
      <ConfirmationDialog
        title='Confirm'
        description='Are you sure?'
        confirmLabel='Yes'
        cancelLabel='No'
        icon='trash-2'
        isOpen={true}
        isSubmitting={false}
        error='Failed to remove item'
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    )

    expect(screen.getByText('Failed to remove item')).toBeInTheDocument()
  })

  it('calls onConfirm and onCancel from the respective actions', async () => {
    const user = userEvent.setup()
    const onConfirm = vi.fn()
    const onCancel = vi.fn()

    render(
      <ConfirmationDialog
        title='Confirm'
        description='Are you sure?'
        confirmLabel='Confirm'
        cancelLabel='Cancel'
        icon='trash-2'
        isOpen={true}
        isSubmitting={false}
        onConfirm={onConfirm}
        onCancel={onCancel}
      />,
    )

    const confirmButton = screen.getByRole('button', { name: 'Confirm' })
    const cancelButton = screen.getByRole('button', { name: 'Cancel' })

    await user.click(confirmButton)
    expect(onConfirm).toHaveBeenCalledOnce()

    await user.click(cancelButton)
    expect(onCancel).toHaveBeenCalledOnce()
  })

  it('calls onCancel from the isolated top-right close action', async () => {
    const user = userEvent.setup()
    const onCancel = vi.fn()

    render(
      <ConfirmationDialog
        title='Confirm'
        description='Are you sure?'
        confirmLabel='Confirm'
        cancelLabel='Cancel'
        icon='trash-2'
        isOpen={true}
        isSubmitting={false}
        onConfirm={vi.fn()}
        onCancel={onCancel}
      />,
    )

    await user.click(screen.getByRole('button', { name: 'Fechar' }))
    expect(onCancel).toHaveBeenCalledOnce()
  })

  it('does not close on outside overlay interaction', async () => {
    const onCancel = vi.fn()

    const { container } = render(
      <ConfirmationDialog
        title='Confirm'
        description='Are you sure?'
        confirmLabel='Confirm'
        cancelLabel='Cancel'
        icon='trash-2'
        isOpen={true}
        isSubmitting={false}
        onConfirm={vi.fn()}
        onCancel={onCancel}
      />,
    )

    const overlay = container.querySelector('[role="alertdialog"]')?.parentElement
    if (overlay) {
      await userEvent.click(overlay)
    }

    expect(onCancel).not.toHaveBeenCalled()
  })
})
