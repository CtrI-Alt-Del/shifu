import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { StreakReminderCard } from '..'
import { useStreakReminderCard } from '../use-streak-reminder-card'

vi.mock('../use-streak-reminder-card', () => ({
  useStreakReminderCard: vi.fn(),
}))

const useStreakReminderCardMock = vi.mocked(useStreakReminderCard)

const handlers = {
  handleSwitchChange: vi.fn(),
  handleHourChange: vi.fn(),
  handleRetry: vi.fn(),
}

function mockCard(overrides: Partial<ReturnType<typeof useStreakReminderCard>> = {}) {
  useStreakReminderCardMock.mockReturnValue({
    hour: 18,
    isLoading: false,
    hasError: false,
    isEnabled: true,
    isSwitching: false,
    isHourPending: false,
    notice: null,
    ...handlers,
    ...overrides,
  })
}

describe('StreakReminderCard', () => {
  afterEach(cleanup)

  beforeEach(() => {
    for (const handler of Object.values(handlers)) handler.mockReset()
    mockCard()
  })

  it('shows the loading skeleton without any control', () => {
    mockCard({ isLoading: true })
    render(<StreakReminderCard />)

    expect(screen.getByRole('region', { name: 'Lembrete de sequência' })).toHaveAttribute(
      'aria-busy',
      'true',
    )
    expect(screen.queryByRole('switch')).not.toBeInTheDocument()
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
  })

  it('shows a recoverable error state without controls', async () => {
    const user = userEvent.setup()
    mockCard({ hasError: true })
    render(<StreakReminderCard />)

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Não foi possível carregar os lembretes agora.',
    )
    expect(screen.queryByRole('switch')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    expect(handlers.handleRetry).toHaveBeenCalledOnce()
  })

  it('renders the enabled state with the stated label and the stored hour', () => {
    render(<StreakReminderCard />)

    const card = screen.getByRole('region', { name: 'Lembrete de sequência' })
    expect(
      within(card).getByText(
        'Receba uma notificação no horário escolhido quando você ainda não praticou no dia, para não perder sua sequência.',
      ),
    ).toBeVisible()
    const switchControl = within(card).getByRole('switch', {
      name: 'Lembrete de sequência Ativados',
    })
    expect(switchControl).toBeChecked()
    expect(switchControl).toBeEnabled()
    expect(
      within(card).getByRole('combobox', { name: 'Horário do lembrete' }),
    ).toHaveTextContent('18:00')
    expect(
      within(card).getByText(
        'Escolha uma hora cheia entre 06:00 e 22:00, no seu fuso horário. A escolha vale para todos os seus navegadores.',
      ),
    ).toBeVisible()
    expect(within(card).queryByRole('status')).not.toBeInTheDocument()
  })

  it('renders the disabled state with the stated label', () => {
    mockCard({ isEnabled: false })
    render(<StreakReminderCard />)

    const switchControl = screen.getByRole('switch', {
      name: 'Lembrete de sequência Desativados',
    })
    expect(switchControl).not.toBeChecked()
  })

  it('toggles the switch by pointer and by keyboard', async () => {
    const user = userEvent.setup()
    render(<StreakReminderCard />)
    const switchControl = screen.getByRole('switch', {
      name: 'Lembrete de sequência Ativados',
    })

    await user.click(switchControl)
    expect(handlers.handleSwitchChange).toHaveBeenLastCalledWith(false, expect.anything())

    handlers.handleSwitchChange.mockClear()
    switchControl.focus()
    await user.keyboard(' ')
    expect(handlers.handleSwitchChange).toHaveBeenCalledOnce()
  })

  it('offers the whole-hour options and reports the chosen hour by keyboard', async () => {
    const user = userEvent.setup()
    render(<StreakReminderCard />)

    screen.getByRole('combobox', { name: 'Horário do lembrete' }).focus()
    await user.keyboard('{Enter}')

    const options = await screen.findAllByRole('option')
    expect(options.map((option) => option.textContent)).toEqual(
      Array.from(
        { length: 17 },
        (_, index) => `${String(index + 6).padStart(2, '0')}:00`,
      ),
    )
    await user.click(screen.getByRole('option', { name: '20:00' }))
    expect(handlers.handleHourChange).toHaveBeenCalledWith('20', expect.anything())
  })

  it('moves through the switch and the hour select with the Tab key', async () => {
    const user = userEvent.setup()
    render(<StreakReminderCard />)

    await user.tab()
    expect(
      screen.getByRole('switch', { name: 'Lembrete de sequência Ativados' }),
    ).toHaveFocus()
    await user.tab()
    expect(screen.getByRole('combobox', { name: 'Horário do lembrete' })).toHaveFocus()
  })

  it('disables the switch while it is saving', () => {
    mockCard({ isSwitching: true })
    render(<StreakReminderCard />)

    expect(
      screen.getByRole('switch', { name: 'Lembrete de sequência Ativados' }),
    ).toHaveAttribute('aria-disabled', 'true')
  })

  it('keeps the hour select focusable but busy while the hour is saving and shows the pending hour', () => {
    mockCard({ isHourPending: true, hour: 20 })
    render(<StreakReminderCard />)

    const select = screen.getByRole('combobox', { name: 'Horário do lembrete' })
    expect(select).toBeEnabled()
    expect(select).toHaveAttribute('aria-busy', 'true')
    expect(select).toHaveAttribute('aria-readonly', 'true')
    expect(select).toHaveTextContent('20:00')
  })

  it('explains in text that notifications are blocked in this browser', () => {
    mockCard({ notice: 'blocked' })
    render(<StreakReminderCard />)

    const notice = screen.getByRole('status')
    expect(notice).toHaveTextContent('Notificações bloqueadas neste navegador')
    expect(notice).toHaveTextContent(
      'Para receber o lembrete aqui, permita notificações do Shifu nas configurações do navegador. Seus outros navegadores continuam recebendo normalmente.',
    )
    expect(
      screen.getByRole('switch', { name: 'Lembrete de sequência Ativados' }),
    ).toBeInTheDocument()
  })

  it('explains in text that this browser cannot receive notifications', () => {
    mockCard({ notice: 'unsupported' })
    render(<StreakReminderCard />)

    const notice = screen.getByRole('status')
    expect(notice).toHaveTextContent('Este navegador não recebe notificações')
    expect(notice).toHaveTextContent('abra o Shifu em um navegador compatível')
  })
})
