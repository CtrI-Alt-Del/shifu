import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ProfileForm } from '..'
import { useProfileForm } from '../use-profile-form'
vi.mock('../use-profile-form', () => ({ useProfileForm: vi.fn() }))
const useProfileFormMock = vi.mocked(useProfileForm)
const PROFILE = {
  accountId: 'a',
  displayName: 'Maria',
  email: 'm@example.com',
  timeZone: 'UTC',
  appearance: 'dark' as const,
}
function createResult(
  overrides: Partial<ReturnType<typeof useProfileForm>> = {},
): ReturnType<typeof useProfileForm> {
  return {
    alertRef: { current: null },
    appearance: 'dark',
    appearanceHelp: 'O Shifu usa o tema escuro em todos os seus dispositivos.',
    appearanceOptions: [
      { value: 'dark', label: 'Escuro' },
      { value: 'light', label: 'Claro' },
      { value: 'system', label: 'Sistema' },
    ],
    displayName: 'Maria',
    email: PROFILE.email,
    errors: {},
    isPending: false,
    isSuccess: false,
    isSuggestedTimeZone: false,
    message: null,
    refreshWarning: null,
    timeZone: 'UTC',
    timeZoneOptions: [{ value: 'UTC', label: 'Tempo universal coordenado · UTC' }],
    handleAppearanceChange: vi.fn(),
    handleDisplayNameChange: vi.fn(),
    handleTimeZoneChange: vi.fn(),
    handleSubmit: vi.fn((event) => event.preventDefault()),
    ...overrides,
  }
}
describe('ProfileForm', () => {
  afterEach(cleanup)
  beforeEach(() => useProfileFormMock.mockReturnValue(createResult()))
  it('renders canonical data, readonly email and localized selected timezone', () => {
    render(<ProfileForm profile={PROFILE} />)
    expect(screen.getByRole('form', { name: 'Perfil da conta' })).toHaveAttribute(
      'method',
      'post',
    )
    expect(screen.getByLabelText('Nome de exibição')).toHaveValue('Maria')
    expect(screen.getByLabelText('E-mail · não editável')).toHaveAttribute('readonly')
    expect(screen.getByLabelText('Fuso horário')).toHaveTextContent(
      'Tempo universal coordenado · UTC',
    )
  })
  it('renders the appearance field after the timezone with its localized value and help', () => {
    render(<ProfileForm profile={PROFILE} />)
    const comboboxes = screen.getAllByRole('combobox')
    expect(comboboxes).toHaveLength(2)
    expect(comboboxes[0]).toBe(screen.getByLabelText('Fuso horário'))
    expect(comboboxes[1]).toBe(screen.getByLabelText('Aparência'))
    expect(comboboxes[1]).toHaveTextContent('Escuro')
    expect(comboboxes[1]).toHaveAccessibleDescription(
      'O Shifu usa o tema escuro em todos os seus dispositivos.',
    )
  })
  it('shows the appearance field error and disables the field while saving', () => {
    useProfileFormMock.mockReturnValue(
      createResult({
        isPending: true,
        appearance: 'light',
        errors: { appearance: 'Confira o campo informado.' },
      }),
    )
    render(<ProfileForm profile={PROFILE} />)
    const field = screen.getByLabelText('Aparência')
    expect(field).toHaveTextContent('Claro')
    expect(field).toHaveAttribute('aria-invalid', 'true')
    expect(field).toHaveAccessibleDescription('Confira o campo informado.')
    expect(field).toBeDisabled()
  })
  it('wires edits and submission through the owning hook', () => {
    const result = createResult()
    useProfileFormMock.mockReturnValue(result)
    render(<ProfileForm profile={PROFILE} />)
    fireEvent.change(screen.getByLabelText('Nome de exibição'), {
      target: { value: 'Ana' },
    })
    fireEvent.submit(screen.getByRole('form', { name: 'Perfil da conta' }))
    expect(result.handleDisplayNameChange).toHaveBeenCalledWith('Ana')
    expect(result.handleSubmit).toHaveBeenCalledOnce()
  })
  it('announces pending, validation, browser suggestion, success and refresh warning', () => {
    useProfileFormMock.mockReturnValue(
      createResult({
        isPending: true,
        errors: { displayName: 'Informe seu nome.' },
        isSuggestedTimeZone: true,
        message: 'Revise os campos.',
      }),
    )
    const { rerender } = render(<ProfileForm profile={PROFILE} />)
    expect(screen.getByRole('button', { name: 'Salvando…' })).toBeDisabled()
    expect(screen.getByLabelText('Nome de exibição')).toHaveAttribute(
      'aria-invalid',
      'true',
    )
    expect(screen.getByRole('alert')).toHaveTextContent('Revise os campos.')
    expect(screen.getByText(/ainda não foi salvo/)).toBeVisible()
    useProfileFormMock.mockReturnValue(
      createResult({
        isSuccess: true,
        message: 'Perfil salvo.',
        refreshWarning: 'Atualize o menu.',
      }),
    )
    rerender(<ProfileForm profile={PROFILE} />)
    expect(screen.getAllByRole('status')).toHaveLength(2)
    expect(screen.getByRole('button', { name: 'Salvar' })).toBeEnabled()
  })
})
