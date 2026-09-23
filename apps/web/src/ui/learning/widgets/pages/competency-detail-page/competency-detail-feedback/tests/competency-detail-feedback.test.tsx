import type { ComponentProps } from 'react'

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { CompetencyDetailFeedback } from '..'

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
  goalId: '01SHF000000000000000000003',
  skillId: '01SHF000000000000000000004',
}

describe('CompetencyDetailFeedback', () => {
  afterEach(cleanup)

  it('announces loading without exposing interactive content', () => {
    render(<CompetencyDetailFeedback state='loading' />)

    expect(
      screen.getByRole('status', { name: 'Carregando Competência e seu progresso...' }),
    ).toHaveTextContent('Carregando Competência e seu progresso...')
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
  })

  it('keeps private absence generic and omits detail fields', () => {
    render(<CompetencyDetailFeedback state='private-absence' />)

    expect(screen.getByRole('heading', { name: 'Recurso não encontrado' })).toBeVisible()
    expect(screen.getByRole('status')).not.toHaveTextContent('Estruturas de repetição')
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
  })

  it('renders the restricted state with only safe Skill navigation', () => {
    render(
      <CompetencyDetailFeedback
        focusCompetencyName='Fundamentos de lógica'
        goalId={IDS.goalId}
        skillId={IDS.skillId}
        state='unavailable'
      />,
    )

    expect(
      screen.getByRole('heading', { name: 'Competência ainda indisponível' }),
    ).toBeVisible()
    expect(screen.getByText(/Fundamentos de lógica/)).toBeVisible()
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
    expect(screen.queryByRole('list')).not.toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: 'Voltar para a Habilidade' }),
    ).toHaveAttribute('data-params', JSON.stringify(IDS))
  })

  it('announces the recoverable failure and delegates one explicit retry', () => {
    const retryMock = vi.fn()
    render(<CompetencyDetailFeedback onRetry={retryMock} state='error' />)

    expect(
      screen.getByRole('alert', { name: 'Não foi possível carregar esta Competência' }),
    ).toHaveTextContent('Seu progresso continua salvo.')
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    expect(retryMock).toHaveBeenCalledOnce()
  })
})
