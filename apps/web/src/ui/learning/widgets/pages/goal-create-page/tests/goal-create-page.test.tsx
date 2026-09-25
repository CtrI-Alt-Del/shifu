import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { GoalCreatePage } from '..'
import { useGoalCreatePage } from '../use-goal-create-page'

vi.mock('../use-goal-create-page', () => ({ useGoalCreatePage: vi.fn() }))

const useGoalCreatePageMock = vi.mocked(useGoalCreatePage)
const SKILL_ID = '01SHF000000000000000000001'

function controller(overrides: Partial<ReturnType<typeof useGoalCreatePage>> = {}) {
  return {
    title: 'Aprender lógica',
    description: 'Praticar fundamentos',
    selectedSkillIds: [],
    skills: [{ id: SKILL_ID, name: 'Lógica', available: true, unavailableReason: null }],
    isLoadingSkills: false,
    hasSkillsError: false,
    isSubmitting: false,
    submissionError: null,
    setTitle: vi.fn(),
    setDescription: vi.fn(),
    handleToggleSkill: vi.fn(),
    handleRetrySkills: vi.fn(async () => ({}) as never),
    handleSubmit: vi.fn(async () => {}),
    ...overrides,
  } as ReturnType<typeof useGoalCreatePage>
}

describe('GoalCreatePage', () => {
  afterEach(cleanup)

  it('lets the learner choose an available Skill before starting its diagnosis', () => {
    const handleToggleSkill = vi.fn()
    useGoalCreatePageMock.mockReturnValue(controller({ handleToggleSkill }))
    render(<GoalCreatePage />)

    expect(screen.getByLabelText('Título do Objetivo *')).toHaveValue('Aprender lógica')
    expect(screen.getByText(/diagnóstico começa quando você iniciar/i)).toBeVisible()
    fireEvent.click(screen.getByRole('checkbox', { name: 'Lógica' }))
    expect(handleToggleSkill).toHaveBeenCalledWith(SKILL_ID)
    expect(screen.getByRole('button', { name: 'Criar Objetivo' })).toBeEnabled()
  })

  it('preserves entered fields and offers retry after submission failure', () => {
    useGoalCreatePageMock.mockReturnValue(
      controller({
        submissionError:
          'Não foi possível criar o Objetivo. Seus dados continuam aqui; tente novamente.',
      }),
    )
    render(<GoalCreatePage />)
    expect(screen.getByRole('alert')).toHaveTextContent('Seus dados continuam aqui')
    expect(screen.getByLabelText('Descrição *')).toHaveValue('Praticar fundamentos')
  })

  it('explains a selected Skill coverage gap without discarding the form', () => {
    useGoalCreatePageMock.mockReturnValue(
      controller({
        selectedSkillIds: [SKILL_ID],
        submissionError:
          'Uma das Habilidades escolhidas ainda não tem cobertura suficiente no Currículo. Revise a seleção; seus dados continuam aqui.',
      }),
    )
    render(<GoalCreatePage />)
    expect(screen.getByRole('alert')).toHaveTextContent('Revise a seleção')
    expect(screen.getByLabelText('Título do Objetivo *')).toHaveValue('Aprender lógica')
    expect(screen.getByRole('checkbox', { name: 'Lógica' })).toBeChecked()
  })
})
