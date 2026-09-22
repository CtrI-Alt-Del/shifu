import type { ComponentProps } from 'react'

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { CompetencyContentRow } from '..'

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
  goalId: '01SHF000000000000000000003',
  materialId: '01SHF000000000000000000006',
  skillId: '01SHF000000000000000000004',
}

describe('CompetencyContentRow', () => {
  afterEach(cleanup)

  it('renders a Material without score or recommendation and preserves context', () => {
    render(
      <CompetencyContentRow
        competencyId={IDS.competencyId}
        goalId={IDS.goalId}
        isRecommended={false}
        item={{
          id: IDS.materialId,
          kind: 'material',
          position: 1,
          title: 'Repetição com for',
        }}
        skillId={IDS.skillId}
      />,
    )

    expect(screen.getByText('Material de apoio')).toBeVisible()
    expect(screen.queryByText(/Nota/)).not.toBeInTheDocument()
    expect(screen.queryByText('Recomendada')).not.toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: 'Repetição com for — Material de apoio' }),
    ).toHaveAttribute(
      'data-to',
      '/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/materials/$materialId',
    )
  })

  it('renders Activity type, localized difficulty and score', () => {
    render(
      <CompetencyContentRow
        competencyId={IDS.competencyId}
        goalId={IDS.goalId}
        isRecommended={false}
        item={{
          activityType: 'learning',
          difficulty: 'medium',
          id: IDS.materialId,
          kind: 'activity',
          latestScore: 80,
          position: 2,
          title: 'Somar uma lista',
        }}
        skillId={IDS.skillId}
      />,
    )

    expect(screen.getByText('Atividade · Média · Nota 80')).toBeVisible()
    expect(screen.getByRole('link', { name: /Somar uma lista/ })).toHaveAttribute(
      'data-to',
      '/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId',
    )
  })

  it('marks a recommended Activity with text and a reachable practice action', () => {
    render(
      <CompetencyContentRow
        competencyId={IDS.competencyId}
        goalId={IDS.goalId}
        isRecommended
        item={{
          activityType: 'learning',
          difficulty: 'hard',
          id: IDS.materialId,
          kind: 'activity',
          latestScore: null,
          position: 3,
          title: 'Somar os números pares de uma lista',
        }}
        skillId={IDS.skillId}
      />,
    )

    expect(screen.getByText('Difícil · Recomendada')).toBeVisible()
    expect(screen.getByText('Praticar')).toBeVisible()
    expect(screen.queryByText(/Nota/)).not.toBeInTheDocument()
  })
})
