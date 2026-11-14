import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  RestartPlanningDialog,
  type RestartPlanningDialogProps,
} from '../restart-planning-dialog'

function renderDialog(overrides: Partial<RestartPlanningDialogProps> = {}) {
  const props: RestartPlanningDialogProps = {
    isOpen: true,
    initialIntent: 'Quero automatizar tarefas com Python.',
    isSubmitting: false,
    errorMessage: null,
    restoreFocusRef: { current: null },
    onClose: vi.fn(),
    onSubmit: vi.fn(),
    ...overrides,
  }
  const rendered = render(<RestartPlanningDialog {...props} />)
  return {
    props,
    ...rendered,
    rerenderWith: (next: Partial<RestartPlanningDialogProps>) =>
      rendered.rerender(<RestartPlanningDialog {...props} {...next} />),
  }
}

describe('RestartPlanningDialog', () => {
  afterEach(cleanup)

  it('returns the focus to the trigger when it closes (CA-07)', async () => {
    const trigger = document.createElement('button')
    document.body.appendChild(trigger)
    const focus = vi.spyOn(trigger, 'focus')
    const { rerenderWith } = renderDialog({ restoreFocusRef: { current: trigger } })

    const dialog = screen.getByRole('alertdialog', { name: 'Reiniciar planejamento' })
    expect(within(dialog).getByLabelText('O que você quer aprender?')).toHaveFocus()
    rerenderWith({ isOpen: false })

    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    // Radix restores the focus on the next macrotask after the content unmounts.
    await waitFor(() => expect(focus).toHaveBeenCalled())
    trigger.remove()
  })

  it('closes without a trigger to focus and submits the typed intention', () => {
    const { props, rerenderWith } = renderDialog()

    const dialog = screen.getByRole('alertdialog', { name: 'Reiniciar planejamento' })
    fireEvent.change(within(dialog).getByLabelText('O que você quer aprender?'), {
      target: { value: ' Quero aprender APIs web ' },
    })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Iniciar planejamento' }))
    expect(props.onSubmit).toHaveBeenCalledWith('Quero aprender APIs web')

    fireEvent.click(within(dialog).getByRole('button', { name: 'Fechar' }))
    expect(props.onClose).toHaveBeenCalledOnce()
    rerenderWith({ isOpen: false })
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
  })
})
