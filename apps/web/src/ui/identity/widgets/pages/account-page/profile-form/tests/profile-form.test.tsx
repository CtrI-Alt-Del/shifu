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
}
function createResult(
  overrides: Partial<ReturnType<typeof useProfileForm>> = {},
): ReturnType<typeof useProfileForm> {
  return {
    alertRef: { current: null },
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
    expect(screen.getByRole('combobox')).toHaveTextContent(
      'Tempo universal coordenado · UTC',
    )
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
