import type { ComponentProps } from 'react'

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { MaterialHeader } from '..'

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
  skillId: '01SHF000000000000000000004',
}

function renderHeader(competencyName = 'Estruturas de repetição') {
  render(
    <MaterialHeader
      competencyId={IDS.competencyId}
      competencyName={competencyName}
      goalId={IDS.goalId}
      materialTitle='Repetição com for'
      skillId={IDS.skillId}
      skillName='Lógica de programação'
    />,
  )
}

describe('MaterialHeader', () => {
  afterEach(() => {
    cleanup()
  })

  it('presents the material title as the page heading', () => {
    renderHeader()

    expect(
      screen.getByRole('heading', { level: 1, name: 'Repetição com for' }),
    ).toBeVisible()
  })

  it('places the material inside its Skill and Competency context', () => {
    renderHeader()

    expect(
      screen.getByText('Lógica de programação · Estruturas de repetição'),
    ).toBeVisible()
    expect(screen.getByText('Material de apoio')).toBeVisible()
  })

  it('returns to the Competency of the route with its explicit params', () => {
    renderHeader()

    const back = screen.getByRole('link', {
      name: 'Voltar para a Competência Estruturas de repetição',
    })

    expect(back).toHaveAttribute(
      'data-to',
      '/learning/goals/$goalId/skills/$skillId/competencies/$competencyId',
    )
    expect(back).toHaveAttribute('data-params', JSON.stringify(IDS))
  })

  it('names the Competency of origin when the same material is reached elsewhere', () => {
    renderHeader('Funções')

    expect(
      screen.getByRole('link', { name: 'Voltar para a Competência Funções' }),
    ).toBeVisible()
    expect(screen.getByText('Lógica de programação · Funções')).toBeVisible()
  })
})
