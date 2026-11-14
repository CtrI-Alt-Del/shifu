import { act, renderHook } from '@testing-library/react'
import type { FormEvent } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  type RestartPlanningDialogProps,
  useRestartPlanningDialog,
} from '../restart-planning-dialog/use-restart-planning-dialog'

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
  const rendered = renderHook(
    (current: RestartPlanningDialogProps) => useRestartPlanningDialog(current),
    { initialProps: props },
  )
  return { props, ...rendered }
}

function submitEvent() {
  return { preventDefault: vi.fn() } as unknown as FormEvent<HTMLFormElement>
}

describe('useRestartPlanningDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('prefills the active intention and resets it on every opening (CA-06)', () => {
    const { result, props, rerender } = renderDialog({ isOpen: false })

    act(() => result.current.handleIntentChange('rascunho'))
    rerender({ ...props, isOpen: true })
    expect(result.current.intent).toBe('Quero automatizar tarefas com Python.')
    expect(result.current.validationMessage).toBeNull()

    act(() => result.current.handleIntentChange('Quero aprender APIs web'))
    rerender({ ...props, isOpen: false })
    rerender({ ...props, isOpen: true })
    expect(result.current.intent).toBe('Quero automatizar tarefas com Python.')
  })

  it('rejects an empty or oversized intention before submitting', () => {
    const { result, props } = renderDialog()

    act(() => result.current.handleIntentChange('   '))
    act(() => result.current.handleSubmit(submitEvent()))
    expect(result.current.validationMessage).toBe(
      'Descreva o que você quer aprender antes de continuar.',
    )
    expect(props.onSubmit).not.toHaveBeenCalled()

    act(() => result.current.handleIntentChange('x'.repeat(4001)))
    expect(result.current.validationMessage).toBeNull()
    act(() => result.current.handleSubmit(submitEvent()))
    expect(result.current.validationMessage).toBe(
      'Resuma sua intenção em até 4000 caracteres.',
    )
    expect(props.onSubmit).not.toHaveBeenCalled()
  })

  it('submits the trimmed intention once and blocks duplicates while submitting', () => {
    const { result, props, rerender } = renderDialog()
    const event = submitEvent()

    act(() => result.current.handleIntentChange('  Quero aprender APIs web  '))
    act(() => result.current.handleSubmit(event))

    expect(event.preventDefault).toHaveBeenCalledOnce()
    expect(props.onSubmit).toHaveBeenCalledWith('Quero aprender APIs web')

    rerender({ ...props, isSubmitting: true })
    act(() => result.current.handleSubmit(submitEvent()))
    expect(props.onSubmit).toHaveBeenCalledTimes(1)
  })

  it('moves the initial focus to the text area instead of the close button', () => {
    const { result } = renderDialog()
    const event = { preventDefault: vi.fn() } as unknown as Event

    act(() => result.current.handleOpenAutoFocus(event))

    expect(event.preventDefault).toHaveBeenCalledOnce()
  })
})
