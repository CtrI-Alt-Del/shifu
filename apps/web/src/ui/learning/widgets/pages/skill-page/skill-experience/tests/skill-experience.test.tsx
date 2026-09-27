import type { ComponentProps } from 'react'

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { SkillExperienceDetail } from '@/core/learning/skill-experience'

import { SkillExperience } from '..'

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

const IDS = {
  goalId: '01SHF000000000000000000001',
  skillId: '01SHF000000000000000000002',
  firstCompetencyId: '01SHF000000000000000000003',
  focusCompetencyId: '01SHF000000000000000000004',
  blockedCompetencyId: '01SHF000000000000000000005',
  activityId: '01SHF000000000000000000006',
  attemptId: '01SHF000000000000000000007',
  evaluationId: '01SHF000000000000000000008',
}

function detail(overrides: Partial<SkillExperienceDetail> = {}): SkillExperienceDetail {
  return {
    goalId: IDS.goalId,
    skillId: IDS.skillId,
    skillName: 'Lógica de programação',
    skillStatus: 'learning',
    overallResult: 72.4,
    focusCompetencyId: IDS.focusCompetencyId,
    focusCompetencyName: 'Estruturas de repetição',
    competencies: [
      {
        competencyId: IDS.firstCompetencyId,
        competencyName: 'Variáveis e tipos',
        position: 1,
        progress: 92,
        status: 'mastered',
        availability: 'available',
        isFocus: false,
      },
      {
        competencyId: IDS.focusCompetencyId,
        competencyName: 'Estruturas de repetição',
        position: 2,
        progress: 72,
        status: 'proficient',
        availability: 'available',
        isFocus: true,
      },
      {
        competencyId: IDS.blockedCompetencyId,
        competencyName: 'Funções',
        position: 3,
        progress: 35,
        status: 'learning',
        availability: 'unavailable',
        isFocus: false,
      },
    ],
    recommendation: {
      competencyId: IDS.focusCompetencyId,
      competencyName: 'Estruturas de repetição',
      activityId: IDS.activityId,
      activityTitle: 'Somar os números pares de uma lista',
      difficulty: 'hard',
      type: 'new-activity',
    },
    evaluation: null,
    ...overrides,
  }
}

function renderExperience(
  overrides: Partial<SkillExperienceDetail> = {},
  state: { isRetrying?: boolean; retryFailed?: boolean } = {},
) {
  const onRetryEvaluation = vi.fn()
  render(
    <SkillExperience
      experience={detail(overrides)}
      isRetrying={state.isRetrying ?? false}
      onRemove={vi.fn()}
      onRetryEvaluation={onRetryEvaluation}
      retryFailed={state.retryFailed ?? false}
    />,
  )
  return { onRetryEvaluation }
}

const HELD_FAILURE = {
  evaluationId: IDS.evaluationId,
  attemptId: IDS.attemptId,
  activityId: IDS.activityId,
  competencyId: IDS.focusCompetencyId,
  status: 'failed',
} as const

describe('SkillExperience', () => {
  afterEach(cleanup)

  it('presents the name, situation and overall result of the Skill', () => {
    renderExperience()

    expect(
      screen.getByRole('heading', { level: 1, name: 'Lógica de programação' }),
    ).toBeVisible()
    expect(screen.getByText('Em aprendizado')).toBeVisible()
    expect(screen.getByText('Resultado geral').parentElement).toHaveTextContent(
      'Resultado geral72%',
    )
  })

  it('lists every Competency in curricular order with progress and situation', () => {
    renderExperience()

    const items = screen.getAllByRole('listitem')
    expect(items).toHaveLength(3)
    expect(items[0]).toHaveTextContent('Variáveis e tipos')
    expect(items[0]).toHaveTextContent('92%')
    expect(items[0]).toHaveTextContent('Dominada')
    expect(items[1]).toHaveTextContent('Estruturas de repetição')
    expect(items[1]).toHaveTextContent('Proficiente')
    expect(items[1]).toHaveTextContent('Em foco')
    expect(items[2]).toHaveTextContent('Funções')
    expect(items[2]).toHaveTextContent('Bloqueada')
  })

  it('links a released Competency to its detail route', () => {
    renderExperience()

    const released = screen.getByRole('link', { name: /Variáveis e tipos/ })
    expect(released).toHaveAttribute(
      'href',
      '/learning/goals/$goalId/skills/$skillId/competencies/$competencyId',
    )
    expect(JSON.parse(released.dataset.params ?? '{}')).toMatchObject({
      competencyId: IDS.firstCompetencyId,
      goalId: IDS.goalId,
      skillId: IDS.skillId,
    })
  })

  it('keeps a blocked Competency on the page and explains the requirement', () => {
    renderExperience()

    expect(screen.queryByRole('link', { name: /Funções/ })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /Funções/ }))

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Funções ainda está bloqueada. Avance em Estruturas de repetição para liberar o conteúdo dela.',
    )
  })

  it('offers the recommendation of the focus Competency and a manual alternative', () => {
    renderExperience()

    expect(screen.getByText('Somar os números pares de uma lista')).toBeVisible()
    expect(screen.getByText('Difícil')).toBeVisible()
    expect(screen.getByText('Atividade nova')).toBeVisible()

    const practice = screen.getByRole('link', { name: 'Continuar praticando' })
    expect(JSON.parse(practice.dataset.params ?? '{}')).toMatchObject({
      activityId: IDS.activityId,
      competencyId: IDS.focusCompetencyId,
    })

    const another = screen.getByRole('link', { name: 'Escolher outra' })
    expect(another).toHaveAttribute(
      'href',
      '/learning/goals/$goalId/skills/$skillId/competencies/$competencyId',
    )
  })

  it('omits the recommendation block when there is none', () => {
    renderExperience({ recommendation: null })

    expect(
      screen.queryByRole('link', { name: 'Continuar praticando' }),
    ).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Escolher outra' })).not.toBeInTheDocument()
  })

  it('announces a running evaluation without a result and without a recommendation', () => {
    renderExperience({
      evaluation: {
        evaluationId: IDS.evaluationId,
        attemptId: IDS.attemptId,
        activityId: IDS.activityId,
        competencyId: IDS.focusCompetencyId,
        status: 'pending',
      },
    })

    expect(screen.getByRole('status')).toHaveTextContent('Avaliando sua resposta')
    expect(screen.getByRole('status')).toHaveTextContent(
      'Novas tentativas desta Habilidade estão pausadas',
    )
    expect(
      screen.queryByRole('link', { name: 'Continuar praticando' }),
    ).not.toBeInTheDocument()
    expect(screen.getAllByRole('listitem')).toHaveLength(3)
  })

  it('recovers a failed evaluation without hiding the released content', () => {
    const { onRetryEvaluation } = renderExperience({
      evaluation: {
        evaluationId: IDS.evaluationId,
        attemptId: IDS.attemptId,
        activityId: IDS.activityId,
        competencyId: IDS.focusCompetencyId,
        status: 'failed',
      },
    })

    expect(screen.getByRole('alert')).toHaveTextContent('A avaliação não pôde terminar')
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))

    expect(onRetryEvaluation).toHaveBeenCalledTimes(1)
    expect(screen.getByRole('link', { name: /Variáveis e tipos/ })).toBeVisible()
  })

  it('reports a retry that could not be processed and blocks a duplicate one', () => {
    renderExperience(
      { evaluation: HELD_FAILURE },
      { isRetrying: true, retryFailed: true },
    )

    const action = screen.getByRole('button', { name: 'Tentando...' })
    expect(action).toBeDisabled()
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Não foi possível reprocessar agora.',
    )
  })

  it('offers the way back to the Objective', () => {
    renderExperience()

    expect(screen.getByRole('link', { name: 'Voltar para o Objetivo' })).toHaveAttribute(
      'href',
      '/learning/goals/$goalId',
    )
  })
})
