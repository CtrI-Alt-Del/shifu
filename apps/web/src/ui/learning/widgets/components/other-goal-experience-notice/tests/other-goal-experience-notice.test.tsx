import { cleanup, render, screen, within } from '@testing-library/react'
import type { ComponentProps } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { SkillExperienceReference } from '@/core/learning/skill-experience-reference'

import { OtherGoalExperienceNotice } from '..'

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

const SKILL_ID = '01J00000000000000000000002'

function createExperience(
  overrides: Partial<SkillExperienceReference> = {},
): SkillExperienceReference {
  return {
    goalId: '01J00000000000000000000004',
    goalTitle: 'Carreira em dados',
    skillExperienceId: '01J00000000000000000000006',
    skillId: SKILL_ID,
    status: 'completed',
    ...overrides,
  }
}

describe('OtherGoalExperienceNotice', () => {
  afterEach(cleanup)

  it('renders nothing for an empty list', () => {
    const { container } = render(<OtherGoalExperienceNotice experiences={[]} />)

    expect(container).toBeEmptyDOMElement()
  })

  it('names the other Goal, its status, the zero start and the link', () => {
    render(<OtherGoalExperienceNotice experiences={[createExperience()]} />)

    const notice = screen.getByRole('region', {
      name: 'Você já tem esta Habilidade em outro Objetivo',
    })
    expect(notice).toHaveTextContent('Você já tem esta Habilidade em outro Objetivo')
    expect(notice).toHaveTextContent(
      'No Objetivo “Carreira em dados”, ela está concluída. Aqui ela começa do zero, com um novo diagnóstico, e nenhum resultado é copiado.',
    )
    const link = within(notice).getByRole('link', { name: 'Ver em Carreira em dados' })
    expect(link).toHaveAttribute('href', '/learning/goals/$goalId/skills/$skillId')
    expect(link).toHaveAttribute(
      'data-params',
      JSON.stringify({ goalId: '01J00000000000000000000004', skillId: SKILL_ID }),
    )
  })

  it('lists each Goal with its own status and link and states the zero start once', () => {
    render(
      <OtherGoalExperienceNotice
        experiences={[
          createExperience(),
          createExperience({
            goalId: '01J00000000000000000000005',
            goalTitle: 'Dados na prática',
            skillExperienceId: '01J00000000000000000000007',
            status: 'learning',
          }),
        ]}
      />,
    )

    const notice = screen.getByRole('region', {
      name: 'Você já tem esta Habilidade em outro Objetivo',
    })
    expect(notice).toHaveTextContent(
      'No Objetivo “Carreira em dados”, ela está concluída.',
    )
    expect(notice).toHaveTextContent(
      'No Objetivo “Dados na prática”, ela está em aprendizado.',
    )
    expect(
      within(notice).getAllByText(/Aqui ela começa do zero, com um novo diagnóstico/),
    ).toHaveLength(1)
    expect(within(notice).getAllByRole('link')).toHaveLength(2)
    expect(
      within(notice).getByRole('link', { name: 'Ver em Dados na prática' }),
    ).toHaveAttribute(
      'data-params',
      JSON.stringify({ goalId: '01J00000000000000000000005', skillId: SKILL_ID }),
    )
  })

  it.each([
    ['not-started', 'não iniciada'],
    ['diagnosing', 'em diagnóstico'],
    ['learning', 'em aprendizado'],
    ['completed', 'concluída'],
  ] as const)('writes the %s status in lowercase pt-BR', (status, label) => {
    render(<OtherGoalExperienceNotice experiences={[createExperience({ status })]} />)

    expect(screen.getByText(new RegExp(`ela está ${label}\\.`))).toBeVisible()
  })
})
