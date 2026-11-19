import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { StreakReminderInvite } from '..'
import { useStreakReminderInvite } from '../use-streak-reminder-invite'

vi.mock('../use-streak-reminder-invite', () => ({
  useStreakReminderInvite: vi.fn(),
}))

const useStreakReminderInviteMock = vi.mocked(useStreakReminderInvite)

const handlers = {
  handleHourChange: vi.fn(),
  handleDecline: vi.fn(),
  handleEnable: vi.fn(),
  handleSaveHour: vi.fn(),
  handleSkip: vi.fn(),
  handleOpenChange: vi.fn(),
  handleOpenAutoFocus: vi.fn(),
  handleCloseAutoFocus: vi.fn(),
  setSelectPortalContainer: vi.fn(),
}

function mockInvite(overrides: Partial<ReturnType<typeof useStreakReminderInvite>> = {}) {
  useStreakReminderInviteMock.mockReturnValue({
    isOpen: true,
    step: 'invite',
    hour: 18,
    isEnabling: false,
    isSavingHour: false,
    selectPortalContainer: null,
    ...handlers,
    ...overrides,
  })
}

describe('StreakReminderInvite', () => {
  afterEach(cleanup)

  beforeEach(() => {
    for (const handler of Object.values(handlers)) handler.mockReset()
    mockInvite()
  })

  it('hands the account email to its owning hook', () => {
    render(<StreakReminderInvite accountEmail='ana@example.com' />)

    expect(useStreakReminderInviteMock).toHaveBeenCalledWith({
      accountEmail: 'ana@example.com',
    })
  })

  it('renders nothing while the invite is closed', () => {
    mockInvite({ isOpen: false })
    render(<StreakReminderInvite accountEmail='ana@example.com' />)

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('explains the benefit and the permission request on the invite step', () => {
    render(<StreakReminderInvite accountEmail='ana@example.com' />)

    const dialog = screen.getByRole('dialog', {
      name: 'Quer um lembrete para manter sua sequência?',
    })
    expect(dialog).toHaveAccessibleDescription(
      'Você praticou hoje e começou uma sequência. Se quiser, o Shifu avisa no horário que você escolher quando você ainda não tiver praticado no dia.',
    )
    expect(
      within(dialog).getByText(
        'O navegador vai pedir sua permissão. Você pode mudar isso depois em Sua conta.',
      ),
    ).toBeVisible()
    expect(within(dialog).getByRole('button', { name: 'Agora não' })).toBeEnabled()
    expect(within(dialog).getByRole('button', { name: 'Ativar lembretes' })).toBeEnabled()
    expect(within(dialog).getByRole('button', { name: 'Fechar' })).toBeEnabled()
  })

  it('moves keyboard focus into the dialog when it opens', () => {
    render(<StreakReminderInvite accountEmail='ana@example.com' />)

    expect(screen.getByRole('dialog')).toContainElement(
      document.activeElement as HTMLElement,
    )
    expect(handlers.handleOpenAutoFocus).toHaveBeenCalled()
  })

  it('keeps the answers in reading order and the same order for the keyboard', () => {
    render(<StreakReminderInvite accountEmail='ana@example.com' />)

    const buttons = within(screen.getByRole('dialog')).getAllByRole('button')

    expect(buttons.map((button) => button.textContent)).toEqual([
      '',
      'Agora não',
      'Ativar lembretes',
    ])
  })

  it('delegates the two answers to the hook', () => {
    render(<StreakReminderInvite accountEmail='ana@example.com' />)

    fireEvent.click(screen.getByRole('button', { name: 'Agora não' }))
    fireEvent.click(screen.getByRole('button', { name: 'Ativar lembretes' }))

    expect(handlers.handleDecline).toHaveBeenCalledOnce()
    expect(handlers.handleEnable).toHaveBeenCalledOnce()
  })

  it('reports a close request from the close button and from Escape', () => {
    render(<StreakReminderInvite accountEmail='ana@example.com' />)

    fireEvent.click(screen.getByRole('button', { name: 'Fechar' }))
    expect(handlers.handleOpenChange).toHaveBeenLastCalledWith(false)

    handlers.handleOpenChange.mockClear()
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' })
    expect(handlers.handleOpenChange).toHaveBeenLastCalledWith(false)
  })

  it('disables both answers and shows the pending text while enabling', () => {
    mockInvite({ isEnabling: true })
    render(<StreakReminderInvite accountEmail='ana@example.com' />)

    expect(screen.getByRole('button', { name: 'Agora não' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Ativando…' })).toBeDisabled()
  })

  it('shows the hour step prefilled with the current hour', () => {
    mockInvite({ step: 'hour', hour: 18 })
    render(<StreakReminderInvite accountEmail='ana@example.com' />)

    const dialog = screen.getByRole('dialog', { name: 'Lembretes ativados' })
    expect(dialog).toHaveAccessibleDescription(
      'Escolha o horário em que prefere ser lembrado. O lembrete só chega se você ainda não tiver praticado no dia.',
    )
    expect(
      within(dialog).getByRole('combobox', { name: 'Horário do lembrete' }),
    ).toHaveTextContent('18:00')
    expect(
      within(dialog).getByText(
        'Hora cheia entre 06:00 e 22:00. Você pode mudar depois em Sua conta.',
      ),
    ).toBeVisible()
    expect(within(dialog).getByRole('button', { name: 'Pular' })).toBeEnabled()
    expect(within(dialog).getByRole('button', { name: 'Salvar horário' })).toBeEnabled()
  })

  it('delegates skipping and saving the hour to the hook', () => {
    mockInvite({ step: 'hour' })
    render(<StreakReminderInvite accountEmail='ana@example.com' />)

    fireEvent.click(screen.getByRole('button', { name: 'Pular' }))
    fireEvent.click(screen.getByRole('button', { name: 'Salvar horário' }))

    expect(handlers.handleSkip).toHaveBeenCalledOnce()
    expect(handlers.handleSaveHour).toHaveBeenCalledOnce()
  })

  it('disables the hour controls and shows the pending text while saving', () => {
    mockInvite({ step: 'hour', isSavingHour: true })
    render(<StreakReminderInvite accountEmail='ana@example.com' />)

    expect(screen.getByRole('combobox', { name: 'Horário do lembrete' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Pular' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Salvando…' })).toBeDisabled()
  })

  it('offers hours from 06:00 to 22:00 inside the dialog and reports the chosen one', async () => {
    const user = userEvent.setup()
    let container: HTMLElement | null = null
    handlers.setSelectPortalContainer.mockImplementation(
      (element: HTMLElement | null) => {
        container = element
      },
    )
    mockInvite({ step: 'hour' })
    const { rerender } = render(<StreakReminderInvite accountEmail='ana@example.com' />)
    mockInvite({ step: 'hour', selectPortalContainer: container })
    rerender(<StreakReminderInvite accountEmail='ana@example.com' />)

    await user.click(screen.getByRole('combobox', { name: 'Horário do lembrete' }))

    const options = await screen.findAllByRole('option')
    expect(options).toHaveLength(17)
    expect(options[0]).toHaveTextContent('06:00')
    expect(options[16]).toHaveTextContent('22:00')
    expect(screen.getByRole('dialog')).toContainElement(options[0])
    await user.click(screen.getByRole('option', { name: '19:00' }))
    expect(handlers.handleHourChange).toHaveBeenCalledWith('19', expect.anything())
  })
})
