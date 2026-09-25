import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, it, expect, vi } from 'vitest'
import { AddSkillFoundationsDialog } from '../index'

describe('AddSkillFoundationsDialog', () => {
  afterEach(cleanup)

  const mockFoundations = [
    { skillId: 'f1', name: 'HTML Basics', status: 'missing' as const },
    { skillId: 'f2', name: 'CSS Basics', status: 'missing' as const },
    { skillId: 'f3', name: 'JavaScript', status: 'present' as const },
  ]

  it('does not render when isOpen is false', () => {
    const { container } = render(
      <AddSkillFoundationsDialog
        skillName='React'
        foundations={mockFoundations}
        isOpen={false}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />,
    )

    expect(container.firstChild).toBeNull()
  })

  it('renders dialog with skill name and foundations', () => {
    render(
      <AddSkillFoundationsDialog
        skillName='React Fundamentals'
        foundations={mockFoundations}
        isOpen={true}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />,
    )

    expect(screen.getByText(/React Fundamentals/)).toBeInTheDocument()
    expect(screen.getByText('HTML Basics')).toBeInTheDocument()
    expect(screen.getByText('CSS Basics')).toBeInTheDocument()
    expect(screen.getByText('JavaScript')).toBeInTheDocument()
  })

  it('groups missing and present foundations', () => {
    render(
      <AddSkillFoundationsDialog
        skillName='React'
        foundations={mockFoundations}
        isOpen={true}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />,
    )

    expect(screen.getByText(/Bases ausentes \(2\)/)).toBeInTheDocument()
    expect(screen.getByText(/Bases já presentes \(1\)/)).toBeInTheDocument()
  })

  it('allows toggling foundation selection', async () => {
    const user = userEvent.setup()
    render(
      <AddSkillFoundationsDialog
        skillName='React'
        foundations={mockFoundations}
        isOpen={true}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />,
    )

    const checkboxes = screen.getAllByRole('checkbox')
    expect(checkboxes).toHaveLength(2)

    await user.click(checkboxes[0])
    expect(checkboxes[0]).toBeChecked()

    await user.click(checkboxes[0])
    expect(checkboxes[0]).not.toBeChecked()
  })

  it('disables submit button when no foundations selected', () => {
    render(
      <AddSkillFoundationsDialog
        skillName='React'
        foundations={mockFoundations}
        isOpen={true}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />,
    )

    const submitButton = screen.getByRole('button', { name: /Adicionar/ })
    expect(submitButton).toBeDisabled()
  })

  it('enables submit button when foundations selected', async () => {
    const user = userEvent.setup()
    render(
      <AddSkillFoundationsDialog
        skillName='React'
        foundations={mockFoundations}
        isOpen={true}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />,
    )

    const checkbox = screen.getAllByRole('checkbox')[0]
    await user.click(checkbox)

    const submitButton = screen.getByRole('button', { name: /Adicionar/ })
    expect(submitButton).not.toBeDisabled()
  })

  it('calls onSubmit with selected foundation IDs', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn().mockResolvedValue(undefined)

    render(
      <AddSkillFoundationsDialog
        skillName='React'
        foundations={mockFoundations}
        isOpen={true}
        onClose={vi.fn()}
        onSubmit={onSubmit}
      />,
    )

    const checkboxes = screen.getAllByRole('checkbox')
    await user.click(checkboxes[0])
    await user.click(checkboxes[1])

    const submitButton = screen.getByRole('button', { name: /Adicionar/ })
    await user.click(submitButton)

    expect(onSubmit).toHaveBeenCalledWith(['f1', 'f2'])
  })

  it('calls onClose when cancel is clicked', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()

    render(
      <AddSkillFoundationsDialog
        skillName='React'
        foundations={mockFoundations}
        isOpen={true}
        onClose={onClose}
        onSubmit={vi.fn()}
      />,
    )

    const cancelButton = screen.getByRole('button', { name: /Cancelar/ })
    await user.click(cancelButton)

    expect(onClose).toHaveBeenCalled()
  })

  it('displays error message when error prop is set', () => {
    render(
      <AddSkillFoundationsDialog
        skillName='React'
        foundations={mockFoundations}
        isOpen={true}
        error='Failed to add skill'
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />,
    )

    expect(screen.getByText('Failed to add skill')).toBeInTheDocument()
  })

  it('shows a loading indicator and hides foundations when isLoading is true', () => {
    render(
      <AddSkillFoundationsDialog
        skillName='React'
        foundations={mockFoundations}
        isOpen={true}
        isLoading={true}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />,
    )

    expect(screen.getByText('Carregando...')).toBeInTheDocument()
    expect(screen.queryByText('HTML Basics')).not.toBeInTheDocument()
  })

  it('shows the submitting label and disables both buttons while submitting', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn(() => new Promise<void>(() => {}))

    render(
      <AddSkillFoundationsDialog
        skillName='React'
        foundations={mockFoundations}
        isOpen={true}
        onClose={vi.fn()}
        onSubmit={onSubmit}
      />,
    )

    await user.click(screen.getAllByRole('checkbox')[0])
    await user.click(screen.getByRole('button', { name: /Adicionar/ }))

    const submitButton = screen.getByRole('button', { name: /Adicionando/ })
    expect(submitButton).toBeDisabled()
    expect(screen.getByRole('button', { name: /Cancelar/ })).toBeDisabled()
  })

  it('handles no foundations gracefully', () => {
    render(
      <AddSkillFoundationsDialog
        skillName='React'
        foundations={[]}
        isOpen={true}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />,
    )

    expect(screen.getByText(/Nenhuma base sugerida/)).toBeInTheDocument()
  })
})
