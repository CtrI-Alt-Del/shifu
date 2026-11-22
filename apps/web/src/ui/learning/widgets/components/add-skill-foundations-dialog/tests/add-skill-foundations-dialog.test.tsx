import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import type { ComponentProps } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { SkillExperienceReference } from '@/core/learning/skill-experience-reference'
import type { SuggestedFoundation } from '@/core/learning/suggested-foundation'

import { AddSkillFoundationsDialog, type AddSkillFoundationsDialogProps } from '..'
import { useAddSkillFoundationsDialog } from '../use-add-skill-foundations-dialog'

vi.mock('../use-add-skill-foundations-dialog', () => ({
  useAddSkillFoundationsDialog: vi.fn(),
}))

type LinkMockProps = Omit<ComponentProps<'a'>, 'href'> & {
  params?: Record<string, string>
  to: string
}

vi.mock('@tanstack/react-router', () => ({
  Link: ({ children, params, to, ...props }: LinkMockProps) => (
    <a data-params={JSON.stringify(params)} href={to} {...props}>
      {children}
    </a>
  ),
}))

const useAddSkillFoundationsDialogMock = vi.mocked(useAddSkillFoundationsDialog)
type DialogController = ReturnType<typeof useAddSkillFoundationsDialog>

const MISSING_FOUNDATIONS: SuggestedFoundation[] = [
  { skillId: 'f1', name: 'HTML Basics', status: 'missing' },
  { skillId: 'f2', name: 'CSS Basics', status: 'missing' },
]
const PRESENT_FOUNDATIONS: SuggestedFoundation[] = [
  { skillId: 'f3', name: 'JavaScript', status: 'present' },
]

const OTHER_EXPERIENCE: SkillExperienceReference = {
  goalId: '01J00000000000000000000004',
  goalTitle: 'Carreira em dados',
  skillExperienceId: '01J00000000000000000000006',
  skillId: '01J00000000000000000000002',
  status: 'completed',
}

function createControllerMock(
  overrides: Partial<DialogController> = {},
): DialogController {
  return {
    description: 'Selecione as bases que deseja adicionar',
    hasFoundations: true,
    isSubmitting: false,
    missingFoundations: MISSING_FOUNDATIONS,
    note: 'A Habilidade será adicionada como não iniciada.',
    otherGoalExperiences: [],
    presentFoundations: PRESENT_FOUNDATIONS,
    isFoundationSelected: vi.fn(() => false),
    handleCloseAutoFocus: vi.fn(),
    handleOpenChange: vi.fn(),
    handleSubmit: vi.fn(),
    handleToggle: vi.fn(),
    ...overrides,
  }
}

function renderDialog(props: Partial<AddSkillFoundationsDialogProps> = {}) {
  return render(
    <AddSkillFoundationsDialog
      foundations={[...MISSING_FOUNDATIONS, ...PRESENT_FOUNDATIONS]}
      goalId='01J00000000000000000000001'
      isOpen
      onClose={vi.fn()}
      onSubmit={vi.fn()}
      skillId='01J00000000000000000000002'
      skillName='React Fundamentals'
      {...props}
    />,
  )
}

describe('AddSkillFoundationsDialog', () => {
  beforeEach(() => {
    useAddSkillFoundationsDialogMock.mockReturnValue(createControllerMock())
  })
  afterEach(cleanup)

  it('passes the Goal, the Skill and the callbacks to its owning hook', () => {
    const onClose = vi.fn()
    const onSubmit = vi.fn()
    renderDialog({ onClose, onSubmit })

    expect(useAddSkillFoundationsDialogMock).toHaveBeenCalledWith({
      goalId: '01J00000000000000000000001',
      skillId: '01J00000000000000000000002',
      foundations: [...MISSING_FOUNDATIONS, ...PRESENT_FOUNDATIONS],
      onClose,
      onSubmit,
    })
  })

  it('renders nothing when it is closed', () => {
    renderDialog({ isOpen: false })

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('renders the header with the Skill title, the description and the close action', () => {
    renderDialog()

    const dialog = screen.getByRole('dialog', {
      name: 'Adicionar React Fundamentals?',
    })
    expect(dialog).toHaveAccessibleDescription('Selecione as bases que deseja adicionar')
    expect(within(dialog).getByRole('button', { name: 'Fechar' })).toBeVisible()
  })

  it('groups the missing and the present foundations', () => {
    renderDialog()

    expect(screen.getByRole('heading', { name: 'Bases ausentes (2)' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Bases já presentes (1)' })).toBeVisible()
    expect(screen.getAllByRole('checkbox')).toHaveLength(2)
    expect(screen.getByText('JavaScript')).toBeVisible()
  })

  it('omits the foundation groups for a Skill without suggested bases', () => {
    useAddSkillFoundationsDialogMock.mockReturnValue(
      createControllerMock({
        description: 'Esta Habilidade não possui bases sugeridas no Currículo.',
        hasFoundations: false,
        missingFoundations: [],
        presentFoundations: [],
      }),
    )
    renderDialog({ foundations: [] })

    expect(
      screen.getByText('Esta Habilidade não possui bases sugeridas no Currículo.'),
    ).toBeVisible()
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: /Bases/ })).not.toBeInTheDocument()
  })

  it('reflects the selection and reports a toggled foundation', () => {
    const handleToggleMock = vi.fn()
    useAddSkillFoundationsDialogMock.mockReturnValue(
      createControllerMock({
        handleToggle: handleToggleMock,
        isFoundationSelected: (skillId) => skillId === 'f2',
      }),
    )
    renderDialog()

    expect(screen.getByRole('checkbox', { name: /HTML Basics/ })).not.toBeChecked()
    expect(screen.getByRole('checkbox', { name: /CSS Basics/ })).toBeChecked()

    fireEvent.click(screen.getByRole('checkbox', { name: /HTML Basics/ }))
    expect(handleToggleMock).toHaveBeenCalledWith('f1')
  })

  it('shows the note and keeps the confirmation enabled without selected bases', () => {
    renderDialog()

    expect(
      screen.getByText('A Habilidade será adicionada como não iniciada.'),
    ).toBeVisible()
    expect(screen.getByRole('button', { name: 'Adicionar habilidade' })).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Cancelar' })).toBeEnabled()
  })

  it('delegates the confirmation to the hook', () => {
    const handleSubmitMock = vi.fn()
    useAddSkillFoundationsDialogMock.mockReturnValue(
      createControllerMock({ handleSubmit: handleSubmitMock }),
    )
    renderDialog()

    fireEvent.click(screen.getByRole('button', { name: 'Adicionar habilidade' }))

    expect(handleSubmitMock).toHaveBeenCalledOnce()
  })

  it('shows the pending label and disables every action while submitting', () => {
    useAddSkillFoundationsDialogMock.mockReturnValue(
      createControllerMock({ isSubmitting: true }),
    )
    renderDialog()

    expect(screen.getByRole('button', { name: 'Adicionando...' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Cancelar' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Fechar' })).toBeDisabled()
  })

  it('asks the hook to close from Cancelar, the close button and Escape', () => {
    const handleOpenChangeMock = vi.fn()
    useAddSkillFoundationsDialogMock.mockReturnValue(
      createControllerMock({ handleOpenChange: handleOpenChangeMock }),
    )
    renderDialog()

    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(handleOpenChangeMock).toHaveBeenLastCalledWith(false)

    handleOpenChangeMock.mockClear()
    fireEvent.click(screen.getByRole('button', { name: 'Fechar' }))
    expect(handleOpenChangeMock).toHaveBeenLastCalledWith(false)

    handleOpenChangeMock.mockClear()
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' })
    expect(handleOpenChangeMock).toHaveBeenLastCalledWith(false)
  })

  it('shows a rejected addition inside the dialog', () => {
    renderDialog({ error: 'Não foi possível concluir a solicitação.' })

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Não foi possível concluir a solicitação.',
    )
    expect(screen.getByRole('dialog')).toBeVisible()
  })

  it('hides the foundations and announces loading', () => {
    renderDialog({ isLoading: true })

    expect(screen.getByRole('status')).toHaveTextContent('Carregando...')
    expect(screen.queryByText('HTML Basics')).not.toBeInTheDocument()
  })

  it('renders the other Goal notice with its link above the note and the actions', () => {
    useAddSkillFoundationsDialogMock.mockReturnValue(
      createControllerMock({ otherGoalExperiences: [OTHER_EXPERIENCE] }),
    )
    renderDialog()

    const notice = screen.getByRole('region', {
      name: 'Você já tem esta Habilidade em outro Objetivo',
    })
    expect(notice).toHaveTextContent(
      'No Objetivo “Carreira em dados”, ela está concluída. Aqui ela começa do zero, com um novo diagnóstico, e nenhum resultado é copiado.',
    )
    const link = within(notice).getByRole('link', { name: 'Ver em Carreira em dados' })
    expect(link).toHaveAttribute('href', '/learning/goals/$goalId/skills/$skillId')
    expect(link).toHaveAttribute(
      'data-params',
      JSON.stringify({
        goalId: OTHER_EXPERIENCE.goalId,
        skillId: OTHER_EXPERIENCE.skillId,
      }),
    )

    const note = screen.getByText('A Habilidade será adicionada como não iniciada.')
    const confirmation = screen.getByRole('button', { name: 'Adicionar habilidade' })
    expect(notice.compareDocumentPosition(note)).toBe(Node.DOCUMENT_POSITION_FOLLOWING)
    expect(notice.compareDocumentPosition(confirmation)).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING,
    )
    expect(confirmation).toBeEnabled()
  })

  it('renders no notice when there is no experience in another Goal', () => {
    renderDialog()

    expect(
      screen.queryByText('Você já tem esta Habilidade em outro Objetivo'),
    ).not.toBeInTheDocument()
  })
})
