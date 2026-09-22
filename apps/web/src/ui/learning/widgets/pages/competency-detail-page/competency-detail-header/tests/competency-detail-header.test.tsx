import type { ComponentProps } from 'react'

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { AvailableCompetencyDetail } from '@/core/learning/competency-detail'

import { CompetencyDetailHeader } from '..'

type LinkMockProps = Omit<ComponentProps<'a'>, 'href'> & {
  params?: Record<string, string>
  to: string
}

vi.mock('@tanstack/react-router', () => ({
  Link: ({ children, params, to, ...props }: LinkMockProps) => (
    <a data-params={JSON.stringify(params)} data-to={to} href={to} {...props}>
      {children}
    </a>
  ),
}))

const IDS = {
  competencyId: '01SHF000000000000000000001',
  focusCompetencyId: '01SHF000000000000000000002',
  goalId: '01SHF000000000000000000003',
  skillId: '01SHF000000000000000000004',
}

const detail: AvailableCompetencyDetail = {
  availability: 'available',
  competencyId: IDS.competencyId,
  competencyName: 'Estruturas de repetição',
  focusCompetencyId: IDS.focusCompetencyId,
  focusCompetencyName: 'Fundamentos de lógica',
  focusReturned: false,
  goalId: IDS.goalId,
  isFocus: true,
  items: [],
  progress: 72,
  skillId: IDS.skillId,
  skillName: 'Lógica de programação',
  status: 'proficient',
  recommendation: null,
}

describe('CompetencyDetailHeader', () => {
  afterEach(cleanup)

  it('renders heading, focus, localized status, progress and typed Skill return', () => {
    render(
      <CompetencyDetailHeader
        detail={detail}
        goalId={IDS.goalId}
        skillId={IDS.skillId}
      />,
    )

    expect(
      screen.getByRole('heading', { level: 1, name: 'Estruturas de repetição' }),
    ).toBeVisible()
    expect(screen.getByText('Em foco')).toBeVisible()
    expect(screen.getByText('Proficiente')).toBeVisible()
    expect(
      screen.getByRole('progressbar', { name: 'Progresso da Competência' }),
    ).toHaveAttribute('aria-valuenow', '72')

    const skillLink = screen.getByRole('link', { name: 'Voltar para a Habilidade' })
    expect(skillLink).toHaveAttribute(
      'data-to',
      '/learning/goals/$goalId/skills/$skillId',
    )
    expect(skillLink).toHaveAttribute(
      'data-params',
      JSON.stringify({ goalId: IDS.goalId, skillId: IDS.skillId }),
    )
  })

  it('explains focus return and keeps non-color state language', () => {
    render(
      <CompetencyDetailHeader
        detail={{ ...detail, focusReturned: true }}
        goalId={IDS.goalId}
        skillId={IDS.skillId}
      />,
    )

    expect(
      screen.getByText(
        'Esta Competência voltou a ser seu foco porque seu progresso atual precisa de reforço.',
      ),
    ).toBeVisible()
    expect(screen.getByText('Em foco')).toBeVisible()
  })

  it('hands a released non-focus learner to the current focus with typed IDs', () => {
    render(
      <CompetencyDetailHeader
        detail={{ ...detail, isFocus: false }}
        goalId={IDS.goalId}
        skillId={IDS.skillId}
      />,
    )

    const focusLink = screen.getByRole('link', { name: /Ir para a Competência em foco/ })
    expect(focusLink).toHaveAttribute(
      'data-to',
      '/learning/goals/$goalId/skills/$skillId/competencies/$competencyId',
    )
    expect(focusLink).toHaveAttribute(
      'data-params',
      JSON.stringify({
        competencyId: IDS.focusCompetencyId,
        goalId: IDS.goalId,
        skillId: IDS.skillId,
      }),
    )
    expect(screen.queryByText('Em foco')).not.toBeInTheDocument()
  })
})
