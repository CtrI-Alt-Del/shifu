import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { LearnerMemoryFaker } from '@/core/intelligence/fakers/learner-memory-faker'

import { MemoryEditForm, type MemoryEditFormProps } from '..'
import { useMemoryEditForm } from '../use-memory-edit-form'

vi.mock('../use-memory-edit-form', () => ({
  MEMORY_CONTENT_MAX_LENGTH: 280,
  useMemoryEditForm: vi.fn(),
}))

const useMemoryEditFormMock = vi.mocked(useMemoryEditForm)
const handleTextareaRefMock = vi.fn()
const handleContentChangeMock = vi.fn()
const handleSubmitMock = vi.fn()
const handleCancelMock = vi.fn()

const memory = LearnerMemoryFaker.fake({
  category: 'recurring_difficulty',
  content: 'Confundo exibir e retornar valores.',
})

function buildProps(overrides: Partial<MemoryEditFormProps> = {}): MemoryEditFormProps {
  return {
    memory,
    isSaving: false,
    saveError: null,
    conflictContent: null,
    onSave: vi.fn(),
    onCancel: vi.fn(),
    ...overrides,
  }
}

describe('MemoryEditForm', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useMemoryEditFormMock.mockReturnValue({
      content: memory.content,
      characterCount: 35,
      visibleError: null,
      handleTextareaRef: handleTextareaRefMock,
      handleContentChange: handleContentChangeMock,
      handleSubmit: (event) => {
        event.preventDefault()
        handleSubmitMock()
      },
      handleCancel: handleCancelMock,
    })
  })
  afterEach(cleanup)

  it('renders the read-only category, the labelled content and the helper text', () => {
    render(<MemoryEditForm {...buildProps()} />)

    expect(screen.getByRole('heading', { name: 'Editar memória' })).toBeVisible()
    expect(screen.getByText('Dificuldades recorrentes')).toBeVisible()
    expect(screen.getByRole('textbox', { name: 'Conteúdo' })).toHaveValue(memory.content)
    expect(
      screen.getByText(/A alteração será usada para adaptar suas explicações/),
    ).toBeVisible()
    expect(screen.getByText('35/280')).toBeVisible()
  })

  it('hands the content field to its hook so focus can move into it', () => {
    render(<MemoryEditForm {...buildProps()} />)

    expect(handleTextareaRefMock).toHaveBeenCalledWith(
      screen.getByRole('textbox', { name: 'Conteúdo' }),
    )
  })

  it('delegates typing, submit and cancel to its hook', async () => {
    const user = userEvent.setup()
    render(<MemoryEditForm {...buildProps()} />)

    fireEvent.change(screen.getByRole('textbox', { name: 'Conteúdo' }), {
      target: { value: 'Novo texto' },
    })
    await user.click(screen.getByRole('button', { name: 'Salvar memória' }))
    await user.click(screen.getByRole('button', { name: 'Cancelar' }))

    expect(handleContentChangeMock).toHaveBeenCalledWith('Novo texto')
    expect(handleSubmitMock).toHaveBeenCalledOnce()
    expect(handleCancelMock).toHaveBeenCalledOnce()
  })

  it('announces a validation error and links it to the field', () => {
    useMemoryEditFormMock.mockReturnValue({
      content: '',
      characterCount: 0,
      visibleError: 'Escreva o conteúdo da memória.',
      handleTextareaRef: handleTextareaRefMock,
      handleContentChange: handleContentChangeMock,
      handleSubmit: handleSubmitMock,
      handleCancel: handleCancelMock,
    })
    render(<MemoryEditForm {...buildProps()} />)

    expect(screen.getByRole('alert')).toHaveTextContent('Escreva o conteúdo da memória.')
    expect(screen.getByRole('textbox', { name: 'Conteúdo' })).toBeInvalid()
  })

  it('disables the controls and labels the pending save', () => {
    render(<MemoryEditForm {...buildProps({ isSaving: true })} />)

    expect(screen.getByRole('textbox', { name: 'Conteúdo' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Salvando…' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Cancelar' })).toBeDisabled()
  })

  it('shows an inline save failure', () => {
    render(
      <MemoryEditForm
        {...buildProps({
          saveError: 'Não foi possível salvar a memória. Tente novamente.',
        })}
      />,
    )

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Não foi possível salvar a memória. Tente novamente.',
    )
    expect(screen.getByRole('button', { name: 'Salvar memória' })).toBeEnabled()
  })

  it('keeps the form open and shows the current content after a conflict', () => {
    render(
      <MemoryEditForm {...buildProps({ conflictContent: 'Texto atual da memória.' })} />,
    )

    const alert = screen.getByRole('alert')
    expect(alert).toHaveTextContent('Esta memória mudou depois que você abriu a edição')
    expect(alert).toHaveTextContent('Conteúdo atual: Texto atual da memória.')
    expect(screen.getByRole('textbox', { name: 'Conteúdo' })).toBeEnabled()
  })
})
