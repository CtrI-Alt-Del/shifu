import type { ComponentProps } from 'react'

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { AvailableCompetencyDetail } from '@/core/learning/competency-detail'

import { CompetencyContentList } from '..'

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
  activityId: '01SHF000000000000000000005',
  competencyId: '01SHF000000000000000000001',
  goalId: '01SHF000000000000000000003',
  materialId: '01SHF000000000000000000006',
  skillId: '01SHF000000000000000000004',
}

const detail: AvailableCompetencyDetail = {
  availability: 'available',
  competencyId: IDS.competencyId,
  competencyName: 'Estruturas de repetição',
  focusCompetencyId: IDS.competencyId,
  focusCompetencyName: 'Estruturas de repetição',
  focusReturned: false,
  goalId: IDS.goalId,
  isFocus: true,
  items: [
    {
      id: IDS.materialId,
      kind: 'material',
      position: 1,
      title: 'Repetição com for',
    },
    {
      activityType: 'learning',
      difficulty: 'easy',
      id: IDS.activityId,
      kind: 'activity',
      latestScore: 100,
      position: 2,
      title: 'Contar de 1 até n',
    },
  ],
  progress: 72,
  recommendation: {
    activityId: IDS.activityId,
    competencyId: IDS.competencyId,
    difficulty: 'easy',
    type: 'new-activity',
  },
  skillId: IDS.skillId,
  skillName: 'Lógica de programação',
  status: 'proficient',
}

describe('CompetencyContentList', () => {
  afterEach(cleanup)

  it('renders each official item once in order and marks only the recommendation', () => {
    render(
      <CompetencyContentList detail={detail} goalId={IDS.goalId} skillId={IDS.skillId} />,
    )

    const rows = screen.getAllByRole('listitem')
    expect(rows).toHaveLength(2)
    expect(rows[0]).toHaveTextContent('Repetição com for')
    expect(rows[1]).toHaveTextContent('Contar de 1 até n')
    expect(
      screen.getByRole('link', { name: 'Repetição com for — Material de apoio' }),
    ).toBeVisible()
    expect(screen.getByRole('link', { name: 'Praticar Contar de 1 até n' })).toBeVisible()
    expect(screen.getByText('Fácil · Recomendada')).toBeVisible()
    expect(
      screen.getByRole('link', { name: 'Praticar Contar de 1 até n' }),
    ).toHaveAttribute(
      'data-params',
      JSON.stringify({
        activityId: IDS.activityId,
        competencyId: IDS.competencyId,
        goalId: IDS.goalId,
        skillId: IDS.skillId,
      }),
    )
  })
})
